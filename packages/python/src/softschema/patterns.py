"""Portable JSON Schema regular-expression profile.

``portable-regex-v1`` keeps an ECMA-262-compatible authoring surface while making
Python's regular-expression behavior match the JavaScript engines used by Node and
Bun.  The compiled schema remains unchanged: only the private copy passed to
``jsonschema`` is lowered to Python equivalents.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from typing import Any, Final, TypeAlias

PORTABLE_PATTERN_PROFILE: Final = "portable-regex-v1"
PORTABLE_PATTERN_MAX_QUANTIFIER: Final = 1000

SchemaPath: TypeAlias = tuple[str | int, ...]
SchemaResource: TypeAlias = bool | dict[str, Any]

_SCHEMA_MAP_KEYWORDS: Final = frozenset(
    {"$defs", "definitions", "dependentSchemas", "patternProperties", "properties"}
)
_SCHEMA_ARRAY_KEYWORDS: Final = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
_SCHEMA_SINGLE_KEYWORDS: Final = frozenset(
    {
        "additionalItems",
        "additionalProperties",
        "contains",
        "contentSchema",
        "else",
        "if",
        "items",
        "not",
        "propertyNames",
        "then",
        "unevaluatedItems",
        "unevaluatedProperties",
    }
)

# ECMA-262 WhiteSpace plus LineTerminator code points.  This is deliberately explicit:
# Python's Unicode ``\s`` also includes U+001C..U+001F, while JavaScript's does not.
_ECMA_WHITESPACE_CLASS: Final = (
    r"\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)
_ANY_CODE_POINT: Final = r"[\s\S]"
_DOT_LOWERING: Final = rf"(?:(?={_ANY_CODE_POINT})(?![\n\r\u2028\u2029]){_ANY_CODE_POINT})"
_SPACE_LOWERING: Final = rf"(?:(?=[{_ECMA_WHITESPACE_CLASS}]){_ANY_CODE_POINT})"
_NONSPACE_LOWERING: Final = rf"(?:(?![{_ECMA_WHITESPACE_CLASS}]){_ANY_CODE_POINT})"

_HEX_DIGITS: Final = frozenset("0123456789abcdefABCDEF")
_ESCAPED_SYNTAX_OUTSIDE: Final = frozenset(r"\.^$*+?{}[]()|")
_ESCAPED_SYNTAX_CLASS: Final = frozenset(r"\[]^-.")


class PortablePatternError(ValueError):
    """Raised when a pattern falls outside ``portable-regex-v1``."""


@dataclass(frozen=True)
class _ClassAtom:
    rendered: str
    code_point: int | None
    direct_operator: str | None = None


class _Parser:
    def __init__(self, pattern: str) -> None:
        self.pattern = pattern
        self.index = 0

    def lower_for_python(self) -> str:
        body = self._expression(terminator=None)
        if self.index != len(self.pattern):
            raise PortablePatternError("unexpected trailing pattern syntax")
        lowered = f"(?a:{body})"
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                re.compile(lowered)
        except (OverflowError, re.error) as exc:
            raise PortablePatternError("pattern does not compile") from exc
        return lowered

    def _expression(self, terminator: str | None) -> str:
        rendered: list[str] = []
        while self.index < len(self.pattern):
            current = self.pattern[self.index]
            if terminator is not None and current == terminator:
                return "".join(rendered)
            if current == "|":
                self.index += 1
                rendered.append("|")
                continue
            rendered.append(self._piece())
        if terminator is not None:
            raise PortablePatternError("unterminated group")
        return "".join(rendered)

    def _piece(self) -> str:
        atom, quantifiable = self._atom()
        if self.index >= len(self.pattern):
            return atom
        current = self.pattern[self.index]
        if current not in "*+?{":
            return atom
        if not quantifiable:
            raise PortablePatternError("assertions cannot be quantified")
        return atom + self._quantifier()

    def _atom(self) -> tuple[str, bool]:
        if self.index >= len(self.pattern):
            raise PortablePatternError("expected an atom")
        current = self.pattern[self.index]
        if current == "(":
            self.index += 1
            prefix = "("
            if self._starts_with("?:"):
                self.index += 2
                prefix = "(?:"
            elif self.index < len(self.pattern) and self.pattern[self.index] == "?":
                raise PortablePatternError("unsupported group construct")
            body = self._expression(terminator=")")
            self.index += 1
            return f"{prefix}{body})", True
        if current == "[":
            return self._character_class(), True
        if current == "\\":
            return self._escape(in_class=False).rendered, True
        if current == ".":
            self.index += 1
            return _DOT_LOWERING, True
        if current == "^":
            self.index += 1
            return "^", False
        if current == "$":
            self.index += 1
            return r"\Z", False
        if current in ")]*+?{}]":
            raise PortablePatternError("unexpected pattern syntax")
        if 0xD800 <= ord(current) <= 0xDFFF:
            raise PortablePatternError("surrogate literals are unsupported")
        self.index += 1
        return current, True

    def _character_class(self) -> str:
        self.index += 1
        rendered = ["["]
        if self.index < len(self.pattern) and self.pattern[self.index] == "^":
            rendered.append("^")
            self.index += 1

        item_count = 0
        previous_operator: str | None = None
        while self.index < len(self.pattern) and self.pattern[self.index] != "]":
            if self.pattern[self.index] == "-" and (
                item_count == 0
                or (self.index + 1 < len(self.pattern) and self.pattern[self.index + 1] == "]")
            ):
                self.index += 1
                start = _ClassAtom("-", ord("-"))
            else:
                start = self._class_atom()
            item_count += 1
            self._reject_future_set_operator(previous_operator, start.direct_operator)
            previous_operator = start.direct_operator

            if (
                self.index < len(self.pattern)
                and self.pattern[self.index] == "-"
                and self.index + 1 < len(self.pattern)
                and self.pattern[self.index + 1] != "]"
            ):
                if start.code_point is None:
                    raise PortablePatternError("class shorthand cannot start a range")
                self.index += 1
                end = self._class_atom()
                if end.code_point is None or start.code_point > end.code_point:
                    raise PortablePatternError("invalid character range")
                rendered.extend((start.rendered, "-", end.rendered))
                previous_operator = end.direct_operator
            else:
                rendered.append(start.rendered)

        if self.index >= len(self.pattern) or item_count == 0:
            raise PortablePatternError("unterminated or empty character class")
        self.index += 1
        rendered.append("]")
        return "".join(rendered)

    def _class_atom(self) -> _ClassAtom:
        if self.index >= len(self.pattern):
            raise PortablePatternError("unterminated character class")
        current = self.pattern[self.index]
        if current == "\\":
            return self._escape(in_class=True)
        if current in "[]-^":
            raise PortablePatternError("class syntax characters must be escaped")
        if 0xD800 <= ord(current) <= 0xDFFF:
            raise PortablePatternError("surrogate literals are unsupported")
        self.index += 1
        direct = current if current in "&|~" else None
        return _ClassAtom(current, ord(current), direct)

    def _escape(self, *, in_class: bool) -> _ClassAtom:
        self.index += 1
        if self.index >= len(self.pattern):
            raise PortablePatternError("dangling escape")
        escaped = self.pattern[self.index]
        self.index += 1

        if escaped in "dDwW":
            return _ClassAtom(f"\\{escaped}", None)
        if escaped in "sS":
            if in_class:
                raise PortablePatternError("whitespace complements in classes are unsupported")
            return _ClassAtom(_SPACE_LOWERING if escaped == "s" else _NONSPACE_LOWERING, None)
        if escaped in "nrtfv":
            code_point = {"n": 10, "r": 13, "t": 9, "f": 12, "v": 11}[escaped]
            return _ClassAtom(f"\\{escaped}", code_point)
        if escaped == "x":
            digits = self._hex_digits(2)
            return _ClassAtom(f"\\x{digits}", int(digits, 16))
        if escaped == "u":
            digits = self._hex_digits(4)
            code_point = int(digits, 16)
            if 0xD800 <= code_point <= 0xDFFF:
                raise PortablePatternError("surrogate escapes are unsupported")
            return _ClassAtom(f"\\u{digits}", code_point)

        allowed = _ESCAPED_SYNTAX_CLASS if in_class else _ESCAPED_SYNTAX_OUTSIDE
        if escaped not in allowed:
            raise PortablePatternError("unsupported escape")
        return _ClassAtom(f"\\{escaped}", ord(escaped))

    def _hex_digits(self, count: int) -> str:
        end = self.index + count
        digits = self.pattern[self.index : end]
        if len(digits) != count or any(char not in _HEX_DIGITS for char in digits):
            raise PortablePatternError("invalid hexadecimal escape")
        self.index = end
        return digits

    def _quantifier(self) -> str:
        current = self.pattern[self.index]
        if current in "*+?":
            self.index += 1
            rendered = current
        else:
            start = self.index
            self.index += 1
            minimum = self._bound()
            maximum = minimum
            if self.index < len(self.pattern) and self.pattern[self.index] == ",":
                self.index += 1
                maximum = None if self._peek() == "}" else self._bound()
            if self._peek() != "}":
                raise PortablePatternError("unterminated bounded quantifier")
            self.index += 1
            if maximum is not None and maximum < minimum:
                raise PortablePatternError("reversed bounded quantifier")
            rendered = self.pattern[start : self.index]

        if self.index < len(self.pattern) and self.pattern[self.index] == "?":
            self.index += 1
            rendered += "?"
        return rendered

    def _bound(self) -> int:
        start = self.index
        while self.index < len(self.pattern) and self.pattern[self.index].isdigit():
            if not self.pattern[self.index].isascii():
                raise PortablePatternError("quantifier bounds must use ASCII digits")
            self.index += 1
        digits = self.pattern[start : self.index]
        if not digits or (len(digits) > 1 and digits[0] == "0"):
            raise PortablePatternError("invalid quantifier bound")
        value = int(digits)
        if value > PORTABLE_PATTERN_MAX_QUANTIFIER:
            raise PortablePatternError("quantifier bound exceeds the profile limit")
        return value

    def _peek(self) -> str | None:
        return self.pattern[self.index] if self.index < len(self.pattern) else None

    def _starts_with(self, value: str) -> bool:
        return self.pattern.startswith(value, self.index)

    @staticmethod
    def _reject_future_set_operator(previous: str | None, current: str | None) -> None:
        if previous is not None and previous == current:
            raise PortablePatternError("ambiguous future character-set operator")


def lower_portable_pattern_for_python(pattern: str) -> str:
    """Validate and lower one v1 pattern to Python ``re`` semantics."""
    return _Parser(pattern).lower_for_python()


def is_portable_pattern(pattern: str) -> bool:
    """Return whether *pattern* belongs to ``portable-regex-v1``."""
    try:
        lower_portable_pattern_for_python(pattern)
    except PortablePatternError:
        return False
    return True


def portable_pattern_matches(pattern: str, value: str) -> bool:
    """Apply the profile's unanchored Unicode-search semantics."""
    lowered = lower_portable_pattern_for_python(pattern)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        return re.search(lowered, value) is not None


def first_unsupported_pattern(
    value: SchemaResource,
    path: SchemaPath = (),
) -> tuple[SchemaPath, str] | None:
    """Find the first unsupported pattern in actual Draft 2020-12 schema positions."""
    if isinstance(value, bool):
        return None

    pattern = value.get("pattern")
    if isinstance(pattern, str) and not is_portable_pattern(pattern):
        return (*path, "pattern"), pattern

    pattern_properties = value.get("patternProperties")
    if isinstance(pattern_properties, dict):
        for candidate in sorted(pattern_properties):
            if isinstance(candidate, str) and not is_portable_pattern(candidate):
                return (*path, "patternProperties", candidate), candidate

    for keyword, child_path, child in _schema_children(value, path):
        del keyword
        nested = first_unsupported_pattern(child, child_path)
        if nested is not None:
            return nested
    return None


def lower_schema_patterns_for_python(
    value: SchemaResource,
) -> tuple[SchemaResource, dict[str, str]]:
    """Deep-copy schema positions, lower patterns, and return error-display reversals."""
    reversals: dict[str, str] = {}

    def lower_node(node: SchemaResource) -> SchemaResource:
        if isinstance(node, bool):
            return node
        lowered: dict[str, Any] = dict(node)

        pattern = node.get("pattern")
        if isinstance(pattern, str):
            engine_pattern = lower_portable_pattern_for_python(pattern)
            reversals[engine_pattern] = pattern
            lowered["pattern"] = engine_pattern

        for keyword in sorted(_SCHEMA_MAP_KEYWORDS):
            mapping = node.get(keyword)
            if not isinstance(mapping, dict):
                continue
            lowered_mapping: dict[str, Any] = {}
            for key in sorted(mapping):
                output_key = key
                if keyword == "patternProperties" and isinstance(key, str):
                    output_key = lower_portable_pattern_for_python(key)
                    reversals[output_key] = key
                child = mapping[key]
                lowered_mapping[output_key] = (
                    lower_node(child) if isinstance(child, bool | dict) else child
                )
            lowered[keyword] = lowered_mapping

        for keyword in sorted(_SCHEMA_ARRAY_KEYWORDS):
            items = node.get(keyword)
            if isinstance(items, list):
                lowered[keyword] = [
                    lower_node(item) if isinstance(item, bool | dict) else item for item in items
                ]

        for keyword in sorted(_SCHEMA_SINGLE_KEYWORDS):
            child = node.get(keyword)
            if isinstance(child, bool | dict):
                lowered[keyword] = lower_node(child)
        return lowered

    return lower_node(value), reversals


def _schema_children(
    node: dict[str, Any],
    path: SchemaPath,
) -> list[tuple[str, SchemaPath, SchemaResource]]:
    children: list[tuple[str, SchemaPath, SchemaResource]] = []
    for keyword in sorted(_SCHEMA_MAP_KEYWORDS):
        mapping = node.get(keyword)
        if not isinstance(mapping, dict):
            continue
        for key in sorted(mapping):
            child = mapping[key]
            if isinstance(child, bool | dict):
                children.append((keyword, (*path, keyword, key), child))
    for keyword in sorted(_SCHEMA_ARRAY_KEYWORDS):
        items = node.get(keyword)
        if not isinstance(items, list):
            continue
        for index, child in enumerate(items):
            if isinstance(child, bool | dict):
                children.append((keyword, (*path, keyword, index), child))
    for keyword in sorted(_SCHEMA_SINGLE_KEYWORDS):
        child = node.get(keyword)
        if isinstance(child, bool | dict):
            children.append((keyword, (*path, keyword), child))
    children.sort(key=lambda item: tuple(str(part) for part in item[1]))
    return children
