"""Bounded parsing and normalization for softschema's portable YAML value domain."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, TypeAlias

from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.events import (
    AliasEvent,
    DocumentEndEvent,
    DocumentStartEvent,
    MappingEndEvent,
    MappingStartEvent,
    ScalarEvent,
    SequenceEndEvent,
    SequenceStartEvent,
    StreamEndEvent,
    StreamStartEvent,
)

MAX_SAFE_INTEGER = 9_007_199_254_740_991
MIB = 1024 * 1024

JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True)
class ValidationLimits:
    """Resource budgets applied at untrusted artifact and schema boundaries."""

    max_resource_bytes: int = 8 * MIB
    max_bundle_bytes: int = 64 * MIB
    max_resources: int = 256
    max_nodes_per_resource: int = 100_000
    max_depth: int = 128
    max_scalar_codepoints: int = MIB

    def __post_init__(self) -> None:
        nonnegative = (
            "max_resource_bytes",
            "max_bundle_bytes",
            "max_scalar_codepoints",
        )
        positive = ("max_resources", "max_nodes_per_resource", "max_depth")
        for name in (*nonnegative, *positive):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
        for name in nonnegative:
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be nonnegative")
        for name in positive:
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be positive")


DEFAULT_VALIDATION_LIMITS = ValidationLimits()


class PortableYamlError(ValueError):
    """Base class for stable portable-YAML boundary failures."""

    def __init__(
        self,
        message: str,
        *,
        path: str = "",
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.line = line
        self.column = column


class PortableYamlSyntaxError(PortableYamlError):
    """The input is not a single syntactically valid YAML document."""


class PortableValueError(PortableYamlError):
    """The input is outside the bounded JSON-compatible value domain."""


@dataclass
class _Budget:
    limits: ValidationLimits
    nodes: int = 0

    def node(
        self,
        path: tuple[str | int, ...],
        depth: int,
        event: Any = None,
        line_offset: int = 0,
    ) -> None:
        if depth > self.limits.max_depth:
            raise _value_error("maximum depth exceeded", path, event, line_offset)
        self.nodes += 1
        if self.nodes > self.limits.max_nodes_per_resource:
            raise _value_error("maximum node count exceeded", path, event, line_offset)

    def scalar(
        self,
        value: str,
        path: tuple[str | int, ...],
        event: Any = None,
        line_offset: int = 0,
    ) -> None:
        if len(value) > self.limits.max_scalar_codepoints:
            raise _value_error("maximum scalar size exceeded", path, event, line_offset)
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise _value_error(
                "string contains an invalid Unicode scalar", path, event, line_offset
            )


_NULL_VALUES = {"", "~", "null", "Null", "NULL"}
_TRUE_VALUES = {"true", "True", "TRUE"}
_FALSE_VALUES = {"false", "False", "FALSE"}
_INTEGER_RE = re.compile(r"[-+]?(?:0|[1-9][0-9_]*|0o[0-7_]+|0x[0-9a-fA-F_]+)\Z")
_FLOAT_RE = re.compile(
    r"[-+]?(?:(?:[0-9][0-9_]*)?\.[0-9_]+(?:[eE][-+]?[0-9]+)?|"
    r"[0-9][0-9_]*(?:\.[0-9_]*)?[eE][-+]?[0-9]+|"
    r"\.(?:inf|Inf|INF|nan|NaN|NAN))\Z"
)
_JSON_SCALAR_TAGS = {
    "tag:yaml.org,2002:str",
    "tag:yaml.org,2002:null",
    "tag:yaml.org,2002:bool",
    "tag:yaml.org,2002:int",
    "tag:yaml.org,2002:float",
}
_MAP_TAG = "tag:yaml.org,2002:map"
_SEQUENCE_TAG = "tag:yaml.org,2002:seq"


def parse_portable_yaml(
    text: str,
    *,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
    encoded_size: int | None = None,
    line_offset: int = 0,
) -> JsonValue:
    """Parse one YAML document after enforcing limits on its event stream."""
    size = len(text.encode("utf-8")) if encoded_size is None else encoded_size
    if size > limits.max_resource_bytes:
        raise PortableValueError("maximum resource size exceeded")

    yaml = YAML(typ="safe", pure=True)
    yaml.version = (1, 2)
    try:
        events = iter(yaml.parse(text))
        _expect_event(events, StreamStartEvent)
        budget = _Budget(limits)
        document_start = next(events)
        if isinstance(document_start, StreamEndEvent):
            budget.node((), 1, document_start, line_offset)
            return None
        if not isinstance(document_start, DocumentStartEvent):
            raise PortableYamlSyntaxError("unexpected YAML document structure")
        first = next(events)
        if isinstance(first, DocumentEndEvent):
            budget.node((), 1, first, line_offset)
            _expect_event(events, StreamEndEvent)
            return None
        value = _parse_event_node(events, first, (), 1, budget, line_offset)
        _expect_event(events, DocumentEndEvent)
        _expect_event(events, StreamEndEvent)
        try:
            next(events)
        except StopIteration:
            return value
        raise PortableYamlSyntaxError("multiple YAML documents are not supported")
    except PortableYamlError:
        raise
    except (StopIteration, YAMLError) as exc:
        mark = getattr(exc, "problem_mark", None)
        line = mark.line + 1 + line_offset if mark is not None else None
        column = mark.column + 1 if mark is not None else None
        raise PortableYamlSyntaxError(
            "invalid YAML syntax",
            line=line,
            column=column,
        ) from exc


def normalize_portable_value(
    value: Any,
    *,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
    encoded_size: int | None = None,
) -> tuple[JsonValue, int]:
    """Normalize an already-materialized value and return its canonical JSON size."""
    if encoded_size is not None and encoded_size > limits.max_resource_bytes:
        raise PortableValueError("maximum resource size exceeded")
    budget = _Budget(limits)
    normalized = _normalize_materialized(value, (), 1, budget, set())
    canonical_size = _canonical_json_size(normalized)
    charged_size = encoded_size if encoded_size is not None else canonical_size
    if charged_size > limits.max_resource_bytes:
        raise PortableValueError("maximum resource size exceeded")
    return normalized, charged_size


def _parse_event_node(
    events: Iterator[Any],
    event: Any,
    path: tuple[str | int, ...],
    depth: int,
    budget: _Budget,
    line_offset: int,
) -> JsonValue:
    budget.node(path, depth, event, line_offset)
    if isinstance(event, AliasEvent):
        raise _value_error("aliases are not portable", path, event, line_offset)
    if isinstance(event, ScalarEvent):
        budget.scalar(event.value, path, event, line_offset)
        return _parse_scalar(event, path, line_offset)
    if isinstance(event, SequenceStartEvent):
        if event.tag not in (None, _SEQUENCE_TAG):
            raise _value_error("tagged sequences are not portable", path, event, line_offset)
        sequence_result: list[JsonValue] = []
        while True:
            child = next(events)
            if isinstance(child, SequenceEndEvent):
                return sequence_result
            index = len(sequence_result)
            sequence_result.append(
                _parse_event_node(events, child, (*path, index), depth + 1, budget, line_offset)
            )
    if isinstance(event, MappingStartEvent):
        if event.tag not in (None, _MAP_TAG):
            raise _value_error("tagged mappings are not portable", path, event, line_offset)
        mapping_result: dict[str, JsonValue] = {}
        while True:
            key_event = next(events)
            if isinstance(key_event, MappingEndEvent):
                return mapping_result
            if not isinstance(key_event, ScalarEvent):
                raise _value_error("mapping keys must be strings", path, key_event, line_offset)
            if key_event.style is None and key_event.tag is None and key_event.value == "<<":
                raise _value_error("merge keys are not portable", path, key_event, line_offset)
            key_value = _parse_event_node(
                events,
                key_event,
                path,
                depth + 1,
                budget,
                line_offset,
            )
            if not isinstance(key_value, str):
                raise _value_error("mapping keys must be strings", path, key_event, line_offset)
            value_path = (*path, key_value)
            if key_value in mapping_result:
                raise _value_error("duplicate mapping key", value_path, key_event, line_offset)
            mapping_result[key_value] = _parse_event_node(
                events,
                next(events),
                value_path,
                depth + 1,
                budget,
                line_offset,
            )
    raise PortableYamlSyntaxError("unexpected YAML event")


def _parse_scalar(
    event: ScalarEvent,
    path: tuple[str | int, ...],
    line_offset: int,
) -> JsonValue:
    tag = event.tag
    if tag is not None and tag not in _JSON_SCALAR_TAGS:
        raise _value_error("YAML tag is not portable", path, event, line_offset)
    if tag == "tag:yaml.org,2002:str" or (tag is None and event.style is not None):
        return event.value
    if tag == "tag:yaml.org,2002:null":
        return None
    if tag == "tag:yaml.org,2002:bool":
        if event.value in _TRUE_VALUES:
            return True
        if event.value in _FALSE_VALUES:
            return False
        raise _value_error("invalid boolean scalar", path, event, line_offset)
    if tag == "tag:yaml.org,2002:int":
        return _parse_integer(event.value, path, event, line_offset)
    if tag == "tag:yaml.org,2002:float":
        return _parse_float(event.value, path, event, line_offset)

    value = event.value
    if value in _NULL_VALUES:
        return None
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    if _INTEGER_RE.fullmatch(value):
        return _parse_integer(value, path, event, line_offset)
    if _FLOAT_RE.fullmatch(value):
        return _parse_float(value, path, event, line_offset)
    return value


def _parse_integer(
    source: str,
    path: tuple[str | int, ...],
    event: Any,
    line_offset: int,
) -> int:
    cleaned = source.replace("_", "")
    sign = -1 if cleaned.startswith("-") else 1
    unsigned = cleaned.lstrip("+-")
    base = 10
    digits = unsigned
    if unsigned.startswith("0o"):
        base, digits = 8, unsigned[2:]
    elif unsigned.startswith("0x"):
        base, digits = 16, unsigned[2:]
    significant = digits.lstrip("0")
    if not significant:
        return 0
    safe_digits = 16 if base == 10 else 18 if base == 8 else 13
    if len(significant) > safe_digits:
        raise _value_error("integer is outside the safe range", path, event, line_offset)
    value = sign * int(digits, base)
    if abs(value) > MAX_SAFE_INTEGER:
        raise _value_error("integer is outside the safe range", path, event, line_offset)
    return value


def _parse_float(
    source: str,
    path: tuple[str | int, ...],
    event: Any,
    line_offset: int,
) -> int | float:
    cleaned = source.replace("_", "")
    if cleaned.lstrip("+-").lower() in {".inf", ".nan"}:
        raise _value_error("number must be finite", path, event, line_offset)
    try:
        exact = Decimal(cleaned)
    except InvalidOperation as exc:
        raise _value_error("invalid numeric scalar", path, event, line_offset) from exc
    if not exact.is_finite():
        raise _value_error("number must be finite", path, event, line_offset)
    if exact == exact.to_integral_value():
        if abs(exact) > MAX_SAFE_INTEGER:
            raise _value_error("integer is outside the safe range", path, event, line_offset)
        return int(exact)
    value = float(exact)
    if not math.isfinite(value):
        raise _value_error("number must be finite", path, event, line_offset)
    if value.is_integer():
        if abs(value) > MAX_SAFE_INTEGER:
            raise _value_error(
                "rounded integer is outside the safe range", path, event, line_offset
            )
        return int(value)
    return value


def _normalize_materialized(
    value: Any,
    path: tuple[str | int, ...],
    depth: int,
    budget: _Budget,
    active: set[int],
) -> JsonValue:
    budget.node(path, depth)
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        budget.scalar(value, path)
        return value
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise _value_error("integer is outside the safe range", path)
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _value_error("number must be finite", path)
        if value.is_integer():
            if abs(value) > MAX_SAFE_INTEGER:
                raise _value_error("rounded integer is outside the safe range", path)
            return int(value)
        return value
    if not isinstance(value, dict | list):
        raise _value_error("value is not JSON-compatible", path)

    identity = id(value)
    if identity in active:
        raise _value_error("cycles are not portable", path)
    active.add(identity)
    try:
        if isinstance(value, list):
            return [
                _normalize_materialized(item, (*path, index), depth + 1, budget, active)
                for index, item in enumerate(value)
            ]
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            budget.node(path, depth + 1)
            if not isinstance(key, str):
                raise _value_error("mapping keys must be strings", path)
            budget.scalar(key, path)
            result[key] = _normalize_materialized(
                item,
                (*path, key),
                depth + 1,
                budget,
                active,
            )
        return result
    finally:
        active.remove(identity)


def _expect_event(events: Iterator[Any], expected: type[Any]) -> Any:
    event = next(events)
    if not isinstance(event, expected):
        raise PortableYamlSyntaxError("unexpected YAML document structure")
    return event


def _canonical_json_size(value: JsonValue) -> int:
    if value is None:
        return 4
    if isinstance(value, bool):
        return 4 if value else 5
    if isinstance(value, int):
        return len(str(value))
    if isinstance(value, float):
        return len(repr(value))
    if isinstance(value, str):
        return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))
    if isinstance(value, list):
        return 2 + max(0, len(value) - 1) + sum(_canonical_json_size(item) for item in value)
    keys = sorted(value)
    return (
        2
        + max(0, len(keys) - 1)
        + sum(_canonical_json_size(key) + 1 + _canonical_json_size(value[key]) for key in keys)
    )


def _value_error(
    message: str,
    path: tuple[str | int, ...],
    event: Any = None,
    line_offset: int = 0,
) -> PortableValueError:
    mark = getattr(event, "start_mark", None)
    return PortableValueError(
        message,
        path=json_pointer(path),
        line=mark.line + 1 + line_offset if mark is not None else None,
        column=mark.column + 1 if mark is not None else None,
    )


def json_pointer(path: tuple[str | int, ...]) -> str:
    """Render a tuple path as an RFC 6901 JSON Pointer."""
    return "".join(f"/{str(part).replace('~', '~0').replace('/', '~1')}" for part in path)
