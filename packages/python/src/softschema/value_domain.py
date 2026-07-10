"""Bounded parsing and normalization for softschema's portable YAML value domain."""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

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
from ruamel.yaml.tokens import DirectiveToken, FlowMappingStartToken, FlowSequenceStartToken

from softschema.core.source_map import NodeSource, SourceMap, SourcePoint, SourceSpan
from softschema.core.value_domain import (
    DEFAULT_VALIDATION_LIMITS as DEFAULT_VALIDATION_LIMITS,
)
from softschema.core.value_domain import (
    MAX_SAFE_INTEGER,
)
from softschema.core.value_domain import (
    JsonValue as JsonValue,
)
from softschema.core.value_domain import (
    PortableValueError as PortableValueError,
)
from softschema.core.value_domain import (
    PortableYamlError as PortableYamlError,
)
from softschema.core.value_domain import (
    PortableYamlSyntaxError as PortableYamlSyntaxError,
)
from softschema.core.value_domain import (
    ValidationLimits as ValidationLimits,
)
from softschema.core.value_domain import (
    normalize_portable_value as normalize_portable_value,
)


@dataclass(frozen=True)
class ParsedPortableYaml:
    """Portable YAML value together with source spans for every materialized node."""

    value: JsonValue
    source_map: SourceMap


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
_TAGGED_INTEGER_RE = re.compile(r"[-+]?(?:[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)\Z")
_TAGGED_FLOAT_RE = re.compile(
    r"[-+]?(?:(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?|"
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
_NONPORTABLE_SOURCE_SEPARATORS = frozenset({"\u0085", "\u2028", "\u2029"})
_NONPORTABLE_SOURCE_SEPARATOR_MESSAGE = "literal YAML source line separator is not portable"
_FLOW_DELIMITERS = frozenset(",]}")
_COMPACT_FLOW_COLON_MESSAGE = "plain compact flow mapping values must be separated after ':'"


def parse_portable_yaml(
    text: str,
    *,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
    encoded_size: int | None = None,
    line_offset: int = 0,
) -> JsonValue:
    """Parse one YAML document after enforcing limits on its event stream."""
    return parse_portable_yaml_with_locations(
        text,
        limits=limits,
        encoded_size=encoded_size,
        line_offset=line_offset,
    ).value


def parse_portable_yaml_with_locations(
    text: str,
    *,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
    encoded_size: int | None = None,
    line_offset: int = 0,
) -> ParsedPortableYaml:
    """Parse portable YAML once and retain immutable key/value source spans."""
    size = len(text.encode("utf-8")) if encoded_size is None else encoded_size
    if size > limits.max_resource_bytes:
        raise PortableValueError("maximum resource size exceeded")
    _reject_nonportable_source_separators(text, line_offset)

    yaml = YAML(typ="safe", pure=True)
    yaml.version = (1, 2)
    _preflight_yaml_syntax(yaml, text, line_offset)
    try:
        events = iter(yaml.parse(text))
        _expect_event(events, StreamStartEvent)
        budget = _Budget(limits)
        locations: dict[str, NodeSource] = {}
        document_start = next(events)
        if isinstance(document_start, StreamEndEvent):
            budget.node((), 1, document_start, line_offset)
            locations[""] = NodeSource(value=_event_span(document_start, line_offset))
            return ParsedPortableYaml(None, SourceMap(locations))
        if not isinstance(document_start, DocumentStartEvent):
            raise PortableYamlSyntaxError("unexpected YAML document structure")
        first = next(events)
        if isinstance(first, DocumentEndEvent):
            budget.node((), 1, first, line_offset)
            _expect_event(events, StreamEndEvent)
            locations[""] = NodeSource(value=_event_span(first, line_offset))
            return ParsedPortableYaml(None, SourceMap(locations))
        value = _parse_event_node(
            events,
            first,
            (),
            1,
            budget,
            line_offset,
            locations,
            text,
        )
        _expect_event(events, DocumentEndEvent)
        _expect_event(events, StreamEndEvent)
        try:
            next(events)
        except StopIteration:
            return ParsedPortableYaml(value, SourceMap(locations))
        raise PortableYamlSyntaxError("multiple YAML documents are not supported")
    except PortableYamlError:
        raise
    except (StopIteration, YAMLError) as exc:
        raise _yaml_syntax_error(exc, line_offset) from exc


def _preflight_yaml_syntax(yaml: YAML, text: str, line_offset: int) -> None:
    """Consume a separate event stream so document syntax wins over prefix semantics."""
    try:
        for token in yaml.scan(text):
            if (
                isinstance(token, DirectiveToken)
                and token.name == "YAML"
                and token.value not in {(1, 1), (1, 2)}
            ):
                raise PortableYamlSyntaxError(
                    "invalid YAML syntax",
                    line=token.start_mark.line + 1 + line_offset,
                    column=token.start_mark.column + 1,
                )
            if isinstance(token, (FlowMappingStartToken, FlowSequenceStartToken)):
                offset = token.end_mark.index
                if text[offset : offset + 1] == "#":
                    raise PortableYamlSyntaxError(
                        "invalid YAML syntax",
                        line=token.end_mark.line + 1 + line_offset,
                        column=token.end_mark.column + 1,
                    )
        for _event in yaml.parse(text):
            pass
    except PortableYamlSyntaxError:
        raise
    except YAMLError as exc:
        raise _yaml_syntax_error(exc, line_offset) from exc


def _yaml_syntax_error(error: BaseException, line_offset: int) -> PortableYamlSyntaxError:
    mark = getattr(error, "problem_mark", None)
    line = mark.line + 1 + line_offset if mark is not None else None
    column = mark.column + 1 if mark is not None else None
    return PortableYamlSyntaxError(
        "invalid YAML syntax",
        line=line,
        column=column,
    )


def _reject_nonportable_source_separators(text: str, line_offset: int) -> None:
    """Reject YAML line-break spellings whose parser semantics differ by runtime."""
    line = 1 + line_offset
    column = 1
    index = 0
    while index < len(text):
        character = text[index]
        if character in _NONPORTABLE_SOURCE_SEPARATORS:
            raise PortableValueError(
                _NONPORTABLE_SOURCE_SEPARATOR_MESSAGE,
                path="",
                line=line,
                column=column,
            )
        if character == "\r":
            index += 2 if text[index + 1 : index + 2] == "\n" else 1
            line += 1
            column = 1
            continue
        if character == "\n":
            index += 1
            line += 1
            column = 1
            continue
        index += 1
        if not (index == 1 and character == "\ufeff"):
            column += 1


def _parse_event_node(
    events: Iterator[Any],
    event: Any,
    path: tuple[str | int, ...],
    depth: int,
    budget: _Budget,
    line_offset: int,
    locations: dict[str, NodeSource],
    text: str,
    *,
    in_flow: bool = False,
) -> JsonValue:
    if isinstance(event, ScalarEvent) and in_flow:
        _reject_plain_compact_flow_colon(event, text, line_offset)
    budget.node(path, depth, event, line_offset)
    pointer = json_pointer(path)
    if isinstance(event, AliasEvent):
        raise _value_error("aliases are not portable", path, event, line_offset)
    if isinstance(event, ScalarEvent):
        budget.scalar(event.value, path, event, line_offset)
        value = _parse_scalar(event, path, line_offset)
        locations[pointer] = NodeSource(value=_scalar_event_span(event, value, text, line_offset))
        return value
    if isinstance(event, SequenceStartEvent):
        if event.tag not in (None, _SEQUENCE_TAG):
            raise _value_error("tagged sequences are not portable", path, event, line_offset)
        sequence_result: list[JsonValue] = []
        while True:
            child = next(events)
            if isinstance(child, SequenceEndEvent):
                locations[pointer] = NodeSource(value=_event_range_span(event, child, line_offset))
                return sequence_result
            index = len(sequence_result)
            sequence_result.append(
                _parse_event_node(
                    events,
                    child,
                    (*path, index),
                    depth + 1,
                    budget,
                    line_offset,
                    locations,
                    text,
                    in_flow=event.flow_style is True,
                )
            )
    if isinstance(event, MappingStartEvent):
        if event.tag not in (None, _MAP_TAG):
            raise _value_error("tagged mappings are not portable", path, event, line_offset)
        mapping_result: dict[str, JsonValue] = {}
        while True:
            key_event = next(events)
            if isinstance(key_event, MappingEndEvent):
                locations[pointer] = NodeSource(
                    value=_event_range_span(event, key_event, line_offset)
                )
                return mapping_result
            if not isinstance(key_event, ScalarEvent):
                raise _value_error("mapping keys must be strings", path, key_event, line_offset)
            if event.flow_style is True:
                _reject_plain_compact_flow_colon(key_event, text, line_offset)
            if key_event.style is None and key_event.tag is None and key_event.value == "<<":
                raise _value_error("merge keys are not portable", path, key_event, line_offset)
            budget.node(path, depth + 1, key_event, line_offset)
            budget.scalar(key_event.value, path, key_event, line_offset)
            key_value = _parse_scalar(key_event, path, line_offset)
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
                locations,
                text,
                in_flow=event.flow_style is True,
            )
            value_pointer = json_pointer(value_path)
            value_source = locations[value_pointer]
            locations[value_pointer] = NodeSource(
                value=value_source.value,
                key=_event_span(key_event, line_offset),
            )
    raise PortableYamlSyntaxError("unexpected YAML event")


def _reject_plain_compact_flow_colon(
    event: ScalarEvent,
    text: str,
    line_offset: int,
) -> None:
    """Reject the plain-flow edge that ruamel.yaml and yaml parse differently."""
    if event.style is not None:
        return
    start = event.start_mark.index
    end = event.end_mark.index
    if end <= start or text[end - 1 : end] != ":" or text[end : end + 1] not in _FLOW_DELIMITERS:
        return
    raise PortableYamlSyntaxError(
        _COMPACT_FLOW_COLON_MESSAGE,
        line=event.end_mark.line + 1 + line_offset,
        column=event.end_mark.column,
    )


def _scalar_event_span(
    event: ScalarEvent,
    value: JsonValue,
    text: str,
    line_offset: int,
) -> SourceSpan:
    if (
        value is None
        and event.value == ""
        and event.style is None
        and event.start_mark.index == event.end_mark.index
    ):
        point = _implicit_null_point(text, event.start_mark, line_offset)
        return SourceSpan(start=point, end=point)
    return _event_span(event, line_offset)


def _implicit_null_point(text: str, mark: Any, line_offset: int) -> SourcePoint:
    """Anchor an empty node at its next line, flow delimiter, comment, or EOF."""
    start = mark.index
    preceding_comment = _preceding_comment_point(text, mark, line_offset)
    if preceding_comment is not None:
        return preceding_comment
    boundary = start
    while text[boundary : boundary + 1] in {" ", "\t"}:
        boundary += 1

    character = text[boundary : boundary + 1]
    if character == "#":
        comment_start = boundary
        while text[boundary : boundary + 1] not in {"", "\r", "\n"}:
            boundary += 1
        character = text[boundary : boundary + 1]
        if character == "":
            boundary = comment_start
    if character == "\r":
        return SourcePoint(line=mark.line + 2 + line_offset, column=1)
    if character == "\n":
        return SourcePoint(line=mark.line + 2 + line_offset, column=1)
    return SourcePoint(
        line=mark.line + 1 + line_offset,
        column=mark.column + boundary - start + 1,
    )


def _preceding_comment_point(
    text: str,
    mark: Any,
    line_offset: int,
) -> SourcePoint | None:
    line_start = max(text.rfind("\r", 0, mark.index), text.rfind("\n", 0, mark.index)) + 1
    separator = text.rfind(":", line_start, mark.index)
    if separator == -1:
        return None
    comment = text.find("#", separator + 1, mark.index)
    if comment != -1 and not text[separator + 1 : comment].strip(" \t"):
        return SourcePoint(
            line=mark.line + 1 + line_offset,
            column=mark.column - (mark.index - comment) + 1,
        )
    return None


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
    if not _TAGGED_INTEGER_RE.fullmatch(cleaned):
        raise _value_error("invalid integer scalar", path, event, line_offset)
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
    try:
        value = sign * int(digits, base)
    except ValueError as exc:
        raise _value_error("invalid integer scalar", path, event, line_offset) from exc
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
    if not _TAGGED_FLOAT_RE.fullmatch(cleaned):
        raise _value_error("invalid numeric scalar", path, event, line_offset)
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


def _expect_event(events: Iterator[Any], expected: type[Any]) -> Any:
    event = next(events)
    if not isinstance(event, expected):
        raise PortableYamlSyntaxError("unexpected YAML document structure")
    return event


def _event_span(event: Any, line_offset: int) -> SourceSpan:
    return SourceSpan(
        start=_mark_point(getattr(event, "start_mark", None), line_offset),
        end=_mark_point(getattr(event, "end_mark", None), line_offset),
    )


def _event_range_span(start_event: Any, end_event: Any, line_offset: int) -> SourceSpan:
    return SourceSpan(
        start=_mark_point(getattr(start_event, "start_mark", None), line_offset),
        end=_mark_point(getattr(end_event, "end_mark", None), line_offset),
    )


def _mark_point(mark: Any, line_offset: int) -> SourcePoint:
    if mark is None:
        return SourcePoint(line=1 + line_offset, column=1)
    return SourcePoint(line=mark.line + 1 + line_offset, column=mark.column + 1)


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
