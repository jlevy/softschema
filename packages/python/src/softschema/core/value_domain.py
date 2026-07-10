"""Portable JSON-compatible values and materialized-value normalization."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, TypeAlias

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
        nonnegative = ("max_resource_bytes", "max_bundle_bytes", "max_scalar_codepoints")
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
    """Base class for stable portable-data boundary failures."""

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


def normalize_portable_value(
    value: Any,
    *,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
    encoded_size: int | None = None,
) -> tuple[JsonValue, int]:
    """Normalize a materialized value and return its canonical JSON size."""
    if encoded_size is not None and encoded_size > limits.max_resource_bytes:
        raise PortableValueError("maximum resource size exceeded")
    budget = _Budget(limits)
    normalized = _normalize_materialized(value, (), 1, budget, set())
    canonical_size = _canonical_json_size(normalized)
    charged_size = encoded_size if encoded_size is not None else canonical_size
    if charged_size > limits.max_resource_bytes:
        raise PortableValueError("maximum resource size exceeded")
    return normalized, charged_size


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
            result[key] = _normalize_materialized(item, (*path, key), depth + 1, budget, active)
        return result
    finally:
        active.remove(identity)


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
