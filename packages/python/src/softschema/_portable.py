"""Bounded UTF-8 and portable YAML input shared by artifact and schema reads."""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.constructor import SafeConstructor
from ruamel.yaml.events import (
    AliasEvent,
    MappingEndEvent,
    MappingStartEvent,
    ScalarEvent,
    SequenceEndEvent,
    SequenceStartEvent,
)
from ruamel.yaml.nodes import ScalarNode

MAX_SAFE_INTEGER = 9_007_199_254_740_991
"""Largest integer that survives a round trip through a JS number.

A portability rule, not a resource guard. Size and shape ceilings were removed: they
only answered whether a hostile document could exhaust the parser, and softschema reads
artifacts its own callers just wrote. The portable-value rules below stay, because they
are what makes a document mean the same thing in both runtimes.
"""


def _construct_timestamp_as_string(_constructor: SafeConstructor, node: ScalarNode) -> str:
    """Keep implicit YAML timestamps inside the portable string domain."""
    return node.value


class _PortableConstructor(SafeConstructor):
    """Safe constructor overrides scoped to softschema parser instances."""


# The first subclass registration copies ruamel's inherited constructor registry.
_PortableConstructor.add_constructor("tag:yaml.org,2002:timestamp", _construct_timestamp_as_string)


class PortableInputError(ValueError):
    """Stable reason for input outside the portable value domain."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def read_utf8(path: Path) -> str:
    """Read one UTF-8 artifact."""
    try:
        return path.read_bytes().decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PortableInputError("invalid_utf8", "input is not valid UTF-8") from exc


def parse_yaml(text: str) -> Any:
    """Parse YAML with the existing library after a representation preflight."""
    yaml = YAML(typ="safe")
    yaml.Constructor = _PortableConstructor
    stack: list[tuple[str, bool]] = []
    has_alias = False

    def consume_parent_slot() -> None:
        if stack and stack[-1][0] == "map":
            kind, expects_key = stack[-1]
            stack[-1] = (kind, not expects_key)

    try:
        for event in yaml.parse(text):
            if isinstance(event, AliasEvent) or getattr(event, "anchor", None) is not None:
                has_alias = True
            if getattr(event, "tag", None) is not None:
                raise PortableInputError("yaml_custom_tag", "explicit YAML tags are not supported")
            if isinstance(event, ScalarEvent):
                if stack and stack[-1] == ("map", True) and event.value == "<<":
                    raise PortableInputError("yaml_merge_key", "YAML merge keys are not supported")
                consume_parent_slot()
            elif isinstance(event, (MappingStartEvent, SequenceStartEvent)):
                consume_parent_slot()
                stack.append(
                    ("map", True) if isinstance(event, MappingStartEvent) else ("seq", False)
                )
            elif isinstance(event, (MappingEndEvent, SequenceEndEvent)):
                stack.pop()
        if has_alias:
            raise PortableInputError("yaml_alias", "YAML aliases and anchors are not supported")
        value = yaml.load(text)
    except PortableInputError:
        raise
    except YAMLError as exc:
        code = "yaml_duplicate_key" if "duplicate key" in str(exc).lower() else "yaml_parse_error"
        raise PortableInputError(code, str(exc)) from exc
    except ValueError as exc:
        raise PortableInputError("yaml_parse_error", str(exc)) from exc
    _check_value(value)
    return value


def _check_value(root: Any) -> None:
    stack: list[Any] = [root]
    while stack:
        value = stack.pop()
        if value is None or isinstance(value, bool):
            continue
        if isinstance(value, str):
            if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
                raise PortableInputError(
                    "yaml_unsupported_scalar", "lone surrogate is not supported"
                )
            continue
        if isinstance(value, int):
            if abs(value) > MAX_SAFE_INTEGER:
                raise PortableInputError("number_out_of_range", "integer exceeds the safe range")
            continue
        if isinstance(value, float):
            if not math.isfinite(value):
                raise PortableInputError("number_out_of_range", "number must be finite")
            if value.hex() == "-0x0.0p+0":
                raise PortableInputError("number_negative_zero", "negative zero is not supported")
            continue
        if isinstance(value, date):
            raise PortableInputError(
                "yaml_unsupported_scalar",
                "host-native date and datetime values are not portable; use an ISO string",
            )
        if isinstance(value, list):
            stack.extend(value)
            continue
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise PortableInputError("yaml_non_string_key", "mapping keys must be strings")
                stack.append(item)
            continue
        raise PortableInputError(
            "yaml_unsupported_scalar", f"unsupported YAML value: {type(value).__name__}"
        )
