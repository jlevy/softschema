"""Bounded UTF-8 and portable YAML input shared by artifact and schema reads."""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.events import (
    AliasEvent,
    MappingEndEvent,
    MappingStartEvent,
    ScalarEvent,
    SequenceEndEvent,
    SequenceStartEvent,
)

MAX_INPUT_BYTES = 1_048_576
MAX_DEPTH = 64
MAX_NODES = 100_000
MAX_SCALAR_BYTES = 262_144
MAX_SAFE_INTEGER = 9_007_199_254_740_991
_TIMESTAMP_SHAPE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[Tt \t]|$)")


class PortableInputError(ValueError):
    """Stable reason for input outside the portable value domain."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def read_utf8(path: Path) -> str:
    """Read one modest UTF-8 file after checking its byte size."""
    size = path.stat().st_size
    if size > MAX_INPUT_BYTES:
        raise PortableInputError(
            "input_too_large", f"input is {size} bytes; limit is {MAX_INPUT_BYTES}"
        )
    try:
        return path.read_bytes().decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PortableInputError("invalid_utf8", "input is not valid UTF-8") from exc


def parse_yaml(text: str) -> Any:
    """Parse YAML with the existing library after a representation preflight."""
    yaml = YAML(typ="safe")
    stack: list[tuple[str, bool]] = []
    nodes = 0
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
                nodes += 1
                if len(event.value.encode("utf-8", errors="surrogatepass")) > MAX_SCALAR_BYTES:
                    raise PortableInputError("yaml_limit", "YAML scalar exceeds the size limit")
                if stack and stack[-1] == ("map", True) and event.value == "<<":
                    raise PortableInputError("yaml_merge_key", "YAML merge keys are not supported")
                if event.style is None and _TIMESTAMP_SHAPE.match(event.value):
                    raise PortableInputError(
                        "yaml_unsupported_scalar", "timestamps are not supported"
                    )
                consume_parent_slot()
            elif isinstance(event, (MappingStartEvent, SequenceStartEvent)):
                nodes += 1
                consume_parent_slot()
                stack.append(
                    ("map", True) if isinstance(event, MappingStartEvent) else ("seq", False)
                )
                if len(stack) > MAX_DEPTH:
                    raise PortableInputError("yaml_limit", "YAML nesting exceeds the depth limit")
            elif isinstance(event, (MappingEndEvent, SequenceEndEvent)):
                stack.pop()
            if nodes > MAX_NODES:
                raise PortableInputError("yaml_limit", "YAML exceeds the node limit")
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
    stack: list[tuple[Any, int]] = [(root, 0)]
    nodes = 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise PortableInputError("yaml_limit", "YAML value exceeds the structure limit")
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
        if isinstance(value, (date, datetime)):
            raise PortableInputError("yaml_unsupported_scalar", "timestamps are not supported")
        if isinstance(value, list):
            stack.extend((item, depth + 1) for item in value)
            continue
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise PortableInputError("yaml_non_string_key", "mapping keys must be strings")
                stack.append((item, depth + 1))
            continue
        raise PortableInputError(
            "yaml_unsupported_scalar", f"unsupported YAML value: {type(value).__name__}"
        )
