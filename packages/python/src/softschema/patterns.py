"""Portable JSON Schema regular-expression profile.

``portable-regex-v1`` is parsed into a bounded Thompson NFA, then matched through
bounded, lazily cached exact DFA subsets. Uncached work has explicit per-match and
per-validation fuel and never delegates untrusted patterns to Python's backtracking
regular-expression engine.

The legacy lowering helper remains available for callers which need a Python
spelling of the portable grammar.  softschema itself uses the NFA at every
validation and matching boundary.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import OrderedDict
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Final, Literal, TypeAlias

PORTABLE_PATTERN_PROFILE: Final = "portable-regex-v1"
PORTABLE_PATTERN_MAX_QUANTIFIER: Final = 1000
PORTABLE_PATTERN_MAX_CODEPOINTS: Final = 1024
PORTABLE_PATTERN_MAX_GROUP_DEPTH: Final = 64
PORTABLE_PATTERN_MAX_NFA_STATES: Final = 4096
PORTABLE_PATTERN_MAX_DFA_STATES: Final = 4096
PORTABLE_PATTERN_MAX_DFA_TRANSITIONS: Final = 4096
PORTABLE_PATTERN_MAX_RETAINED_SUBSET_MEMBERSHIPS: Final = 32_768
PORTABLE_PATTERN_MAX_MATCH_COMPUTE_WORK: Final = 4_194_304
PORTABLE_PATTERN_MAX_VALIDATION_WORK: Final = 8_388_608
PORTABLE_PATTERN_MAX_VALIDATION_MEMO_ENTRIES: Final = 4096
PORTABLE_PATTERN_MAX_VALIDATION_MEMO_CODEPOINTS: Final = 1_048_576
PORTABLE_PATTERN_MAX_SCHEMA_PATTERNS: Final = 256
PORTABLE_PATTERN_MAX_SCHEMA_CODEPOINTS: Final = 16_384
PORTABLE_PATTERN_CACHE_SIZE: Final = 32
PORTABLE_PATTERN_MAX_CACHED_DFA_TRANSITIONS: Final = (
    PORTABLE_PATTERN_CACHE_SIZE * PORTABLE_PATTERN_MAX_DFA_TRANSITIONS
)
PORTABLE_PATTERN_MAX_CACHED_SUBSET_MEMBERSHIPS: Final = (
    PORTABLE_PATTERN_CACHE_SIZE * PORTABLE_PATTERN_MAX_RETAINED_SUBSET_MEMBERSHIPS
)

_MAX_UNICODE_CODE_POINT: Final = 0x10FFFF

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

# ECMA-262 WhiteSpace plus LineTerminator code points.  Python's Unicode ``\s``
# additionally includes U+001C..U+001F, so matching uses this explicit set.
_ECMA_WHITESPACE_CODEPOINTS: Final = frozenset(
    {
        0x0009,
        0x000A,
        0x000B,
        0x000C,
        0x000D,
        0x0020,
        0x00A0,
        0x1680,
        *range(0x2000, 0x200B),
        0x2028,
        0x2029,
        0x202F,
        0x205F,
        0x3000,
        0xFEFF,
    }
)
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


class PortablePatternWorkLimitError(RuntimeError):
    """Raised instead of allowing profile matching work to become unbounded."""


@dataclass(slots=True)
class _ValidationWorkBudget:
    remaining: int
    matches: dict[tuple[str, str], bool] = field(default_factory=dict)
    memo_code_points: int = 0

    def charge(self, amount: int) -> None:
        self.remaining -= amount
        if self.remaining < 0:
            raise PortablePatternWorkLimitError("portable pattern validation work limit exceeded")


_VALIDATION_WORK_BUDGET: ContextVar[_ValidationWorkBudget | None] = ContextVar(
    "softschema_portable_pattern_validation_work",
    default=None,
)


@contextmanager
def portable_pattern_validation_budget(
    limit: int = PORTABLE_PATTERN_MAX_VALIDATION_WORK,
) -> Generator[None, None, None]:
    """Bound aggregate pattern/key work for one synchronous structural validation."""
    token = _VALIDATION_WORK_BUDGET.set(_ValidationWorkBudget(limit))
    try:
        yield
    finally:
        _VALIDATION_WORK_BUDGET.reset(token)


_PredicateKind: TypeAlias = Literal[
    "literal",
    "range",
    "digit",
    "not_digit",
    "word",
    "not_word",
    "space",
    "not_space",
    "dot",
]


@dataclass(frozen=True)
class _Predicate:
    kind: _PredicateKind
    start: int = 0
    end: int = 0

    def matches(self, character: str) -> bool:
        code_point = ord(character)
        if self.kind == "literal":
            return code_point == self.start
        if self.kind == "range":
            return self.start <= code_point <= self.end
        if self.kind == "digit":
            return 0x30 <= code_point <= 0x39
        if self.kind == "not_digit":
            return not 0x30 <= code_point <= 0x39
        if self.kind == "word":
            return (
                0x30 <= code_point <= 0x39
                or 0x41 <= code_point <= 0x5A
                or 0x61 <= code_point <= 0x7A
                or code_point == 0x5F
            )
        if self.kind == "not_word":
            return not (
                0x30 <= code_point <= 0x39
                or 0x41 <= code_point <= 0x5A
                or 0x61 <= code_point <= 0x7A
                or code_point == 0x5F
            )
        if self.kind == "space":
            return code_point in _ECMA_WHITESPACE_CODEPOINTS
        if self.kind == "not_space":
            return code_point not in _ECMA_WHITESPACE_CODEPOINTS
        return code_point not in {0x000A, 0x000D, 0x2028, 0x2029}


@dataclass(frozen=True)
class _Matcher:
    ranges: tuple[tuple[int, int], ...]
    starts: tuple[int, ...]

    def matches(self, character: str) -> bool:
        code_point = ord(character)
        index = bisect_right(self.starts, code_point) - 1
        return index >= 0 and code_point <= self.ranges[index][1]


def _normalize_ranges(
    ranges: Iterator[tuple[int, int]] | tuple[tuple[int, int], ...] | list[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def _complement_ranges(
    ranges: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], ...]:
    complement: list[tuple[int, int]] = []
    cursor = 0
    for start, end in ranges:
        if cursor < start:
            complement.append((cursor, start - 1))
        cursor = end + 1
    if cursor <= _MAX_UNICODE_CODE_POINT:
        complement.append((cursor, _MAX_UNICODE_CODE_POINT))
    return tuple(complement)


def _predicate_ranges(predicate: _Predicate) -> tuple[tuple[int, int], ...]:
    if predicate.kind == "literal":
        return ((predicate.start, predicate.start),)
    if predicate.kind == "range":
        return ((predicate.start, predicate.end),)
    if predicate.kind in {"digit", "not_digit"}:
        ranges = ((0x30, 0x39),)
    elif predicate.kind in {"word", "not_word"}:
        ranges = ((0x30, 0x39), (0x41, 0x5A), (0x5F, 0x5F), (0x61, 0x7A))
    elif predicate.kind in {"space", "not_space"}:
        ranges = _normalize_ranges((point, point) for point in _ECMA_WHITESPACE_CODEPOINTS)
    else:
        ranges = _complement_ranges(((0x000A, 0x000A), (0x000D, 0x000D), (0x2028, 0x2029)))
    if predicate.kind in {"not_digit", "not_word", "not_space"}:
        return _complement_ranges(ranges)
    return ranges


def _matcher_from_predicates(
    predicates: tuple[_Predicate, ...] | list[_Predicate],
    *,
    negated: bool = False,
) -> _Matcher:
    ranges = _normalize_ranges(
        item for predicate in predicates for item in _predicate_ranges(predicate)
    )
    if negated:
        ranges = _complement_ranges(ranges)
    return _Matcher(ranges=ranges, starts=tuple(start for start, _end in ranges))


@dataclass(frozen=True)
class _ClassAtom:
    rendered: str
    predicate: _Predicate
    code_point: int | None
    direct_operator: str | None = None


_NodeKind: TypeAlias = Literal["empty", "char", "start", "end", "concat", "alt", "repeat"]


@dataclass(frozen=True)
class _Node:
    kind: _NodeKind
    children: tuple[_Node, ...] = ()
    matcher: _Matcher | None = None
    minimum: int = 0
    maximum: int | None = 0


@dataclass(frozen=True)
class _ParsedPattern:
    lowered_body: str
    root: _Node
    state_count: int


class _Parser:
    def __init__(self, pattern: str) -> None:
        if len(pattern) > PORTABLE_PATTERN_MAX_CODEPOINTS:
            raise PortablePatternError("pattern exceeds the profile size limit")
        self.pattern = pattern
        self.index = 0
        self.group_depth = 0

    def parse(self) -> _ParsedPattern:
        rendered, root = self._expression(terminator=None)
        if self.index != len(self.pattern):
            raise PortablePatternError("unexpected trailing pattern syntax")
        state_count = _node_state_count(root) + 1
        if state_count > PORTABLE_PATTERN_MAX_NFA_STATES:
            raise PortablePatternError("compiled pattern exceeds the profile state limit")
        return _ParsedPattern(rendered, root, state_count)

    def _expression(self, terminator: str | None) -> tuple[str, _Node]:
        alternatives: list[_Node] = []
        alternative_renderings: list[str] = []
        pieces: list[_Node] = []
        rendered: list[str] = []
        while self.index < len(self.pattern):
            current = self.pattern[self.index]
            if terminator is not None and current == terminator:
                break
            if current == "|":
                self.index += 1
                alternatives.append(_concat(pieces))
                alternative_renderings.append("".join(rendered))
                pieces = []
                rendered = []
                continue
            piece_rendered, piece = self._piece()
            rendered.append(piece_rendered)
            pieces.append(piece)
        if terminator is not None and self.index >= len(self.pattern):
            raise PortablePatternError("unterminated group")
        alternatives.append(_concat(pieces))
        alternative_renderings.append("".join(rendered))
        if len(alternatives) == 1:
            return alternative_renderings[0], alternatives[0]
        return "|".join(alternative_renderings), _Node("alt", tuple(alternatives))

    def _piece(self) -> tuple[str, _Node]:
        rendered, atom, quantifiable = self._atom()
        if self.index >= len(self.pattern) or self.pattern[self.index] not in "*+?{":
            return rendered, atom
        if not quantifiable:
            raise PortablePatternError("assertions cannot be quantified")
        quantifier, minimum, maximum = self._quantifier()
        return rendered + quantifier, _Node(
            "repeat",
            (atom,),
            minimum=minimum,
            maximum=maximum,
        )

    def _atom(self) -> tuple[str, _Node, bool]:
        if self.index >= len(self.pattern):
            raise PortablePatternError("expected an atom")
        current = self.pattern[self.index]
        if current == "(":
            if self.group_depth >= PORTABLE_PATTERN_MAX_GROUP_DEPTH:
                raise PortablePatternError("group nesting exceeds the profile limit")
            self.index += 1
            prefix = "("
            if self._starts_with("?:"):
                self.index += 2
                prefix = "(?:"
            elif self.index < len(self.pattern) and self.pattern[self.index] == "?":
                raise PortablePatternError("unsupported group construct")
            self.group_depth += 1
            try:
                body_rendered, body = self._expression(terminator=")")
            finally:
                self.group_depth -= 1
            self.index += 1
            return f"{prefix}{body_rendered})", body, True
        if current == "[":
            rendered, matcher = self._character_class()
            return rendered, _Node("char", matcher=matcher), True
        if current == "\\":
            atom = self._escape(in_class=False)
            return (
                atom.rendered,
                _Node("char", matcher=_matcher_from_predicates((atom.predicate,))),
                True,
            )
        if current == ".":
            self.index += 1
            return (
                _DOT_LOWERING,
                _Node("char", matcher=_matcher_from_predicates((_Predicate("dot"),))),
                True,
            )
        if current == "^":
            self.index += 1
            return "^", _Node("start"), False
        if current == "$":
            self.index += 1
            return r"\Z", _Node("end"), False
        if current in ")]*+?{}]":
            raise PortablePatternError("unexpected pattern syntax")
        if 0xD800 <= ord(current) <= 0xDFFF:
            raise PortablePatternError("surrogate literals are unsupported")
        self.index += 1
        predicate = _Predicate("literal", ord(current))
        return current, _Node("char", matcher=_matcher_from_predicates((predicate,))), True

    def _character_class(self) -> tuple[str, _Matcher]:
        self.index += 1
        rendered = ["["]
        negated = False
        if self.index < len(self.pattern) and self.pattern[self.index] == "^":
            rendered.append("^")
            negated = True
            self.index += 1

        predicates: list[_Predicate] = []
        item_count = 0
        previous_operator: str | None = None
        while self.index < len(self.pattern) and self.pattern[self.index] != "]":
            if self.pattern[self.index] == "-" and (
                item_count == 0
                or (self.index + 1 < len(self.pattern) and self.pattern[self.index + 1] == "]")
            ):
                self.index += 1
                start = _literal_class_atom("-")
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
                predicates.append(_Predicate("range", start.code_point, end.code_point))
                previous_operator = end.direct_operator
            else:
                rendered.append(start.rendered)
                predicates.append(start.predicate)

        if self.index >= len(self.pattern) or item_count == 0:
            raise PortablePatternError("unterminated or empty character class")
        self.index += 1
        rendered.append("]")
        return "".join(rendered), _matcher_from_predicates(predicates, negated=negated)

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
        return _ClassAtom(
            current,
            _Predicate("literal", ord(current)),
            ord(current),
            current if current in "&|~" else None,
        )

    def _escape(self, *, in_class: bool) -> _ClassAtom:
        self.index += 1
        if self.index >= len(self.pattern):
            raise PortablePatternError("dangling escape")
        escaped = self.pattern[self.index]
        self.index += 1

        if escaped in "dDwW":
            if escaped == "d":
                kind: _PredicateKind = "digit"
            elif escaped == "D":
                kind = "not_digit"
            elif escaped == "w":
                kind = "word"
            else:
                kind = "not_word"
            return _ClassAtom(f"\\{escaped}", _Predicate(kind), None)
        if escaped in "sS":
            if in_class:
                raise PortablePatternError("whitespace complements in classes are unsupported")
            kind = "space" if escaped == "s" else "not_space"
            rendered = _SPACE_LOWERING if escaped == "s" else _NONSPACE_LOWERING
            return _ClassAtom(rendered, _Predicate(kind), None)
        if escaped in "nrtfv":
            code_point = {"n": 10, "r": 13, "t": 9, "f": 12, "v": 11}[escaped]
            return _ClassAtom(
                f"\\{escaped}",
                _Predicate("literal", code_point),
                code_point,
            )
        if escaped == "x":
            digits = self._hex_digits(2)
            return _escaped_code_point(f"\\x{digits}", int(digits, 16))
        if escaped == "u":
            digits = self._hex_digits(4)
            code_point = int(digits, 16)
            if 0xD800 <= code_point <= 0xDFFF:
                raise PortablePatternError("surrogate escapes are unsupported")
            return _escaped_code_point(f"\\u{digits}", code_point)

        allowed = _ESCAPED_SYNTAX_CLASS if in_class else _ESCAPED_SYNTAX_OUTSIDE
        if escaped not in allowed:
            raise PortablePatternError("unsupported escape")
        return _escaped_code_point(f"\\{escaped}", ord(escaped))

    def _hex_digits(self, count: int) -> str:
        end = self.index + count
        digits = self.pattern[self.index : end]
        if len(digits) != count or any(character not in _HEX_DIGITS for character in digits):
            raise PortablePatternError("invalid hexadecimal escape")
        self.index = end
        return digits

    def _quantifier(self) -> tuple[str, int, int | None]:
        current = self.pattern[self.index]
        if current in "*+?":
            self.index += 1
            rendered = current
            minimum, maximum = {
                "*": (0, None),
                "+": (1, None),
                "?": (0, 1),
            }[current]
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
        return rendered, minimum, maximum

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


def _literal_class_atom(character: str) -> _ClassAtom:
    code_point = ord(character)
    return _ClassAtom(character, _Predicate("literal", code_point), code_point)


def _escaped_code_point(rendered: str, code_point: int) -> _ClassAtom:
    return _ClassAtom(rendered, _Predicate("literal", code_point), code_point)


def _concat(children: list[_Node]) -> _Node:
    if not children:
        return _Node("empty")
    if len(children) == 1:
        return children[0]
    return _Node("concat", tuple(children))


def _node_state_count(node: _Node) -> int:
    if node.kind in {"empty", "char", "start", "end"}:
        return 1
    if node.kind == "concat":
        return sum(_node_state_count(child) for child in node.children)
    if node.kind == "alt":
        return sum(_node_state_count(child) for child in node.children) + len(node.children) - 1
    child_cost = _node_state_count(node.children[0])
    if node.maximum is None:
        return node.minimum * child_cost + child_cost + 1
    if node.maximum == 0:
        return 1
    return node.minimum * child_cost + (node.maximum - node.minimum) * (child_cost + 1)


_InstructionKind: TypeAlias = Literal["char", "start", "end", "jump", "split", "accept"]


@dataclass
class _MutableInstruction:
    kind: _InstructionKind
    matcher: _Matcher | None = None
    out1: int = -1
    out2: int = -1


@dataclass(frozen=True)
class _Instruction:
    kind: _InstructionKind
    matcher: _Matcher | None
    out1: int
    out2: int


@dataclass(frozen=True)
class _Fragment:
    start: int
    outs: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class _ReadyState:
    active: tuple[int, ...]
    accepted: bool


@dataclass(slots=True)
class _CompiledPattern:
    instructions: tuple[_Instruction, ...]
    start: int
    _boundaries: tuple[int, ...] = field(init=False, repr=False)
    _closures: dict[int, _ReadyState] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _transitions: dict[tuple[int, bool, int], int] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _pending_states: list[frozenset[int]] = field(
        default_factory=lambda: [frozenset()],
        init=False,
        repr=False,
    )
    _pending_ids: dict[frozenset[int], int] = field(
        default_factory=lambda: {frozenset(): 0},
        init=False,
        repr=False,
    )
    _retained_subset_memberships: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        boundaries = {0, _MAX_UNICODE_CODE_POINT + 1}
        for instruction in self.instructions:
            if instruction.matcher is None:
                continue
            for start, end in instruction.matcher.ranges:
                boundaries.add(start)
                if end < _MAX_UNICODE_CODE_POINT:
                    boundaries.add(end + 1)
        self._boundaries = tuple(sorted(boundaries))

    def search(self, value: str) -> bool:
        compute_work = [PORTABLE_PATTERN_MAX_MATCH_COMPUTE_WORK]
        pending_id = 0
        input_length = len(value)
        for position in range(input_length + 1):
            at_start = position == 0
            at_end = position == input_length
            if not at_start and not at_end and pending_id in self._closures:
                ready = self._closures[pending_id]
            else:
                ready = self._closure(
                    pending_id,
                    at_start=at_start,
                    at_end=at_end,
                    compute_work=compute_work,
                )
                if not at_start and not at_end:
                    if len(self._closures) >= PORTABLE_PATTERN_MAX_DFA_STATES:
                        raise PortablePatternWorkLimitError(
                            "portable pattern DFA-state limit exceeded"
                        )
                    if self._retain_subset_memberships(len(ready.active)):
                        self._closures[pending_id] = ready
            if ready.accepted:
                return True
            if at_end:
                break
            character = value[position]
            class_index = bisect_right(self._boundaries, ord(character)) - 1
            transition_key = (pending_id, at_start, class_index)
            cached = self._transitions.get(transition_key)
            if cached is None:
                self._charge_compute(compute_work, len(ready.active))
                next_pending = frozenset(
                    instruction.out1
                    for index in ready.active
                    if (instruction := self.instructions[index]).matcher is not None
                    and instruction.matcher.matches(character)
                )
                cached, cache_reset = self._intern_pending(next_pending)
                # A membership-budget reset renumbers the retained DFA subsets. The
                # transition was computed from the previous generation, so retaining
                # its old numeric key would be incorrect; the exact current state is
                # still carried forward and can be recomputed on a later match.
                if not cache_reset:
                    if len(self._transitions) >= PORTABLE_PATTERN_MAX_DFA_TRANSITIONS:
                        raise PortablePatternWorkLimitError(
                            "portable pattern DFA-transition limit exceeded"
                        )
                    self._transitions[transition_key] = cached
            pending_id = cached
        return False

    def _closure(
        self,
        pending_id: int,
        *,
        at_start: bool,
        at_end: bool,
        compute_work: list[int],
    ) -> _ReadyState:
        active: list[int] = []
        accepted = False
        visited: set[int] = set()
        stack = [*self._pending_states[pending_id], self.start]
        while stack:
            index = stack.pop()
            if index in visited:
                continue
            visited.add(index)
            self._charge_compute(compute_work, 1)
            instruction = self.instructions[index]
            if instruction.kind == "jump":
                stack.append(instruction.out1)
            elif instruction.kind == "split":
                stack.extend((instruction.out1, instruction.out2))
            elif instruction.kind == "start":
                if at_start:
                    stack.append(instruction.out1)
            elif instruction.kind == "end":
                if at_end:
                    stack.append(instruction.out1)
            elif instruction.kind == "accept":
                accepted = True
            else:
                active.append(index)
        active.sort()
        return _ReadyState(tuple(active), accepted)

    def _intern_pending(self, pending: frozenset[int]) -> tuple[int, bool]:
        existing = self._pending_ids.get(pending)
        if existing is not None:
            return existing, False
        cache_reset = False
        if (
            self._retained_subset_memberships + len(pending)
            > PORTABLE_PATTERN_MAX_RETAINED_SUBSET_MEMBERSHIPS
        ):
            self._reset_dfa_cache()
            cache_reset = True
            existing = self._pending_ids.get(pending)
            if existing is not None:
                return existing, cache_reset
        if len(self._pending_states) >= PORTABLE_PATTERN_MAX_DFA_STATES:
            raise PortablePatternWorkLimitError("portable pattern DFA-state limit exceeded")
        # One pending subset contains at most one member per bounded NFA state, so it
        # must fit in the per-engine membership budget after any reset above.
        if not self._retain_subset_memberships(len(pending)):
            raise AssertionError("portable pattern subset membership accounting drifted")
        identifier = len(self._pending_states)
        self._pending_states.append(pending)
        self._pending_ids[pending] = identifier
        return identifier, cache_reset

    def _retain_subset_memberships(self, amount: int) -> bool:
        if (
            self._retained_subset_memberships + amount
            > PORTABLE_PATTERN_MAX_RETAINED_SUBSET_MEMBERSHIPS
        ):
            return False
        self._retained_subset_memberships += amount
        return True

    def _reset_dfa_cache(self) -> None:
        """Discard reusable DFA state while preserving exact NFA match semantics."""
        self._closures.clear()
        self._transitions.clear()
        self._pending_states[:] = [frozenset()]
        self._pending_ids.clear()
        self._pending_ids[frozenset()] = 0
        self._retained_subset_memberships = 0

    @staticmethod
    def _charge_compute(compute_work: list[int], amount: int) -> None:
        compute_work[0] -= amount
        if compute_work[0] < 0:
            raise PortablePatternWorkLimitError("portable pattern match work limit exceeded")
        validation_budget = _VALIDATION_WORK_BUDGET.get()
        if validation_budget is not None:
            validation_budget.charge(amount)


class _Compiler:
    def __init__(self) -> None:
        self.instructions: list[_MutableInstruction] = []

    def compile(self, root: _Node, expected_states: int) -> _CompiledPattern:
        fragment = self._node(root)
        accept = self._add("accept")
        self._patch(fragment.outs, accept)
        if len(self.instructions) != expected_states:
            raise AssertionError("portable pattern state accounting drifted")
        instructions = tuple(
            _Instruction(item.kind, item.matcher, item.out1, item.out2)
            for item in self.instructions
        )
        return _CompiledPattern(instructions, fragment.start)

    def _node(self, node: _Node) -> _Fragment:
        if node.kind == "empty":
            index = self._add("jump")
            return _Fragment(index, ((index, 1),))
        if node.kind == "char":
            index = self._add("char", matcher=node.matcher)
            return _Fragment(index, ((index, 1),))
        if node.kind in {"start", "end"}:
            index = self._add("start" if node.kind == "start" else "end")
            return _Fragment(index, ((index, 1),))
        if node.kind == "concat":
            first = self._node(node.children[0])
            current = first
            for child in node.children[1:]:
                following = self._node(child)
                self._patch(current.outs, following.start)
                current = _Fragment(first.start, following.outs)
            return current
        if node.kind == "alt":
            branches = [self._node(child) for child in node.children]
            start = branches[-1].start
            for branch in reversed(branches[:-1]):
                start = self._add("split", out1=branch.start, out2=start)
            return _Fragment(start, tuple(out for branch in branches for out in branch.outs))
        return self._repeat(node)

    def _repeat(self, node: _Node) -> _Fragment:
        child = node.children[0]
        fragment: _Fragment | None = None
        for _ in range(node.minimum):
            fragment = self._append(fragment, self._node(child))

        if node.maximum is None:
            repeated = self._node(child)
            split = self._add("split", out1=repeated.start)
            self._patch(repeated.outs, split)
            if fragment is None:
                return _Fragment(split, ((split, 2),))
            self._patch(fragment.outs, split)
            return _Fragment(fragment.start, ((split, 2),))

        for _ in range(node.maximum - node.minimum):
            optional = self._node(child)
            split = self._add("split", out1=optional.start)
            if fragment is None:
                fragment = _Fragment(split, (*optional.outs, (split, 2)))
            else:
                self._patch(fragment.outs, split)
                fragment = _Fragment(fragment.start, (*optional.outs, (split, 2)))
        if fragment is not None:
            return fragment
        index = self._add("jump")
        return _Fragment(index, ((index, 1),))

    def _append(self, first: _Fragment | None, second: _Fragment) -> _Fragment:
        if first is None:
            return second
        self._patch(first.outs, second.start)
        return _Fragment(first.start, second.outs)

    def _add(
        self,
        kind: _InstructionKind,
        *,
        matcher: _Matcher | None = None,
        out1: int = -1,
        out2: int = -1,
    ) -> int:
        self.instructions.append(_MutableInstruction(kind, matcher, out1, out2))
        return len(self.instructions) - 1

    def _patch(self, outs: tuple[tuple[int, int], ...], target: int) -> None:
        for index, slot in outs:
            instruction = self.instructions[index]
            if slot == 1:
                instruction.out1 = target
            else:
                instruction.out2 = target


@lru_cache(maxsize=256)
def _parse_portable_pattern(pattern: str) -> _ParsedPattern:
    return _Parser(pattern).parse()


def _compile_portable_pattern(pattern: str) -> _CompiledPattern:
    cached = _COMPILED_PATTERN_CACHE.get(pattern)
    if cached is not None:
        _COMPILED_PATTERN_CACHE.move_to_end(pattern)
        return cached
    parsed = _parse_portable_pattern(pattern)
    compiled = _Compiler().compile(parsed.root, parsed.state_count)
    _COMPILED_PATTERN_CACHE[pattern] = compiled
    if len(_COMPILED_PATTERN_CACHE) > PORTABLE_PATTERN_CACHE_SIZE:
        _COMPILED_PATTERN_CACHE.popitem(last=False)
    return compiled


_COMPILED_PATTERN_CACHE: OrderedDict[str, _CompiledPattern] = OrderedDict()


def portable_pattern_cache_info() -> tuple[int, int, int]:
    """Return retained pattern, transition, and configured transition-cap counts."""
    return (
        len(_COMPILED_PATTERN_CACHE),
        sum(len(compiled._transitions) for compiled in _COMPILED_PATTERN_CACHE.values()),
        PORTABLE_PATTERN_MAX_CACHED_DFA_TRANSITIONS,
    )


def _portable_pattern_cache_membership_info() -> tuple[int, int, int, int]:  # pyright: ignore[reportUnusedFunction]
    """Return aggregate/peak membership counts and their implementation caps."""
    memberships = [
        compiled._retained_subset_memberships for compiled in _COMPILED_PATTERN_CACHE.values()
    ]
    return (
        sum(memberships),
        max(memberships, default=0),
        PORTABLE_PATTERN_MAX_CACHED_SUBSET_MEMBERSHIPS,
        PORTABLE_PATTERN_MAX_RETAINED_SUBSET_MEMBERSHIPS,
    )


def lower_portable_pattern_for_python(pattern: str) -> str:
    """Validate and lower one v1 pattern to Python ``re`` spelling.

    The returned spelling is for compatibility only; softschema matching uses
    :func:`portable_pattern_matches` and its bounded automaton.
    """
    return f"(?a:{_parse_portable_pattern(pattern).lowered_body})"


def is_portable_pattern(pattern: str) -> bool:
    """Return whether *pattern* belongs to ``portable-regex-v1`` and its budgets."""
    try:
        _compile_portable_pattern(pattern)
    except PortablePatternError:
        return False
    return True


def portable_pattern_matches(pattern: str, value: str) -> bool:
    """Apply bounded, unanchored Unicode-code-point search semantics."""
    validation_budget = _VALIDATION_WORK_BUDGET.get()
    cache_key = (pattern, value)
    if validation_budget is not None:
        cached = validation_budget.matches.get(cache_key)
        if cached is not None:
            return cached
        validation_budget.charge(len(value) + 1)
    result = _compile_portable_pattern(pattern).search(value)
    if validation_budget is not None:
        retained_code_points = len(pattern) + len(value)
        if (
            len(validation_budget.matches) < PORTABLE_PATTERN_MAX_VALIDATION_MEMO_ENTRIES
            and validation_budget.memo_code_points + retained_code_points
            <= PORTABLE_PATTERN_MAX_VALIDATION_MEMO_CODEPOINTS
        ):
            validation_budget.matches[cache_key] = result
            validation_budget.memo_code_points += retained_code_points
    return result


def first_unsupported_pattern(
    value: SchemaResource,
    path: SchemaPath = (),
) -> tuple[SchemaPath, str] | None:
    """Find the first unsupported pattern or aggregate profile-budget crossing."""
    code_point_count = 0
    for pattern_count, (pattern_path, pattern) in enumerate(
        _schema_patterns(value, path),
        start=1,
    ):
        code_point_count += len(pattern)
        if (
            pattern_count > PORTABLE_PATTERN_MAX_SCHEMA_PATTERNS
            or code_point_count > PORTABLE_PATTERN_MAX_SCHEMA_CODEPOINTS
            or not is_portable_pattern(pattern)
        ):
            return pattern_path, pattern
    return None


def _schema_patterns(
    value: SchemaResource,
    path: SchemaPath,
) -> Iterator[tuple[SchemaPath, str]]:
    if isinstance(value, bool):
        return

    pattern = value.get("pattern")
    if isinstance(pattern, str):
        yield (*path, "pattern"), pattern

    pattern_properties = value.get("patternProperties")
    if isinstance(pattern_properties, dict):
        for candidate in sorted(pattern_properties):
            if isinstance(candidate, str):
                yield (*path, "patternProperties", candidate), candidate

    for keyword, child_path, child in _schema_children(value, path):
        del keyword
        yield from _schema_patterns(child, child_path)


def lower_schema_patterns_for_python(
    value: SchemaResource,
) -> tuple[SchemaResource, dict[str, str]]:
    """Compatibility helper which deep-copies and lowers actual schema positions."""
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
