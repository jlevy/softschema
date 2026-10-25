"""A JSON document parses through ``json`` with exactly the result ruamel gives it.

``parse_yaml`` reads a document whose text is strict JSON with :mod:`json` instead of
ruamel's pure-Python parser, and only when the two are known to agree. These tests pin
that agreement three ways:

- explicit outcomes for every input where JSON and YAML 1.2 can disagree, recorded from
  the ruamel path, so a fast path that drifts from today's verdict fails by name;
- equivalence over a corpus of the repo's own documents, each in several JSON
  spellings, and over seeded generated documents that deliberately include every
  disagreement shape, comparing values, types, key order, float bits and error codes;
- checks that a plain JSON document never reaches ruamel at all, and that each listed
  disagreement shape does.
"""

from __future__ import annotations

import json
import math
import random
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import ruamel.yaml
from ruamel.yaml import YAML
from ruamel.yaml.parser import Parser as RuamelParser
from ruamel.yaml.reader import Reader

from softschema import _portable, read_yaml_doc
from softschema._portable import MAX_DEPTH, PortableInputError, parse_yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

requires_json_path = pytest.mark.skipif(
    not _portable._JSON_PATH_ENABLED,
    reason="ruamel's C extension or an unchecked ruamel release keeps every text on the ruamel path",
)
pure_ruamel_only = pytest.mark.skipif(
    YAML(typ="safe").Parser is not RuamelParser,
    reason="libyaml reads this text differently from pure ruamel",
)
slow = pytest.mark.slow
"""Costly evidence, left out of the default run; `uv run pytest -m slow` runs it."""


def _ruamel_path(text: str) -> Any:
    """The unchanged ruamel parse that every JSON fast-path result must equal."""
    return _portable._parse_with_ruamel(text)


Outcome = tuple[str, Any, str]


def _outcome(parse: Callable[[str], Any], text: str) -> Outcome:
    try:
        return ("value", parse(text), "")
    except PortableInputError as exc:
        return ("error", exc.code, str(exc))


def _same(left: Any, right: Any) -> bool:
    """Equal in type, key order, and float bits, which ``==`` does not check."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(_same(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(map(_same, left, right))
    if isinstance(left, float):
        return left.hex() == right.hex() or (math.isnan(left) and math.isnan(right))
    return left == right


def _assert_equivalent(text: str) -> bool:
    """Assert both paths agree on ``text``; return whether the fast path decided it."""
    fast = _outcome(parse_yaml, text)
    slow = _outcome(_ruamel_path, text)
    assert fast[0] == slow[0], (text[:200], fast, slow)
    if fast[0] == "value":
        assert _same(fast[1], slow[1]), (text[:200], fast[1], slow[1])
    else:
        assert fast[1:] == slow[1:], (text[:200], fast, slow)
    return _portable._parse_json_subset(text) is not _portable._NOT_JSON


def _nest(depth: int) -> str:
    """``depth`` simultaneously open collections, alternating arrays and objects."""
    text = "0"
    for level in range(depth):
        text = f'{{"k": {text}}}' if level % 2 else f"[{text}]"
    return text


# --- Explicit outcomes, recorded from the ruamel path ---------------------------------

AS_JSON = object()
"""Expect the plain ``json.loads`` reading, which ruamel agrees with for this input."""

VALUE_CASES: list[tuple[str, str, Any]] = [
    ("compact", '{"a":1,"b":[1,2,{"c":"d"}]}', {"a": 1, "b": [1, 2, {"c": "d"}]}),
    (
        "pretty",
        '{\n  "a": 1,\n  "b": [\n    true,\n    null\n  ]\n}\n',
        {"a": 1, "b": [True, None]},
    ),
    ("tab_indented", '{\n\t"a": 1,\n\t"b": [\n\t\t2\n\t]\n}', {"a": 1, "b": [2]}),
    ("crlf", '{\r\n  "a": 1\r\n}\r\n', {"a": 1}),
    ("column_zero_lines", '{\n"a": [\n1,\n-2\n],\n"b": {}\n}', {"a": [1, -2], "b": {}}),
    ("spaced_colon", '{"a" :1, "b"   :   2}', {"a": 1, "b": 2}),
    # NaN and Infinity are not JSON tokens. ruamel reads them as YAML 1.2 plain
    # scalars, which resolve to strings; ``.nan`` would be the YAML float.
    ("nan", '{"a": NaN}', {"a": "NaN"}),
    ("infinity", '{"a": Infinity}', {"a": "Infinity"}),
    ("negative_infinity", '{"a": -Infinity}', {"a": "-Infinity"}),
    ("max_safe_integer", '{"a": 9007199254740991, "b": -9007199254740991}', AS_JSON),
    # YAML resolves ``-0`` as the integer 0, so it is not a negative zero.
    ("negative_zero_integer", '{"a": -0}', {"a": 0}),
    ("positive_zero_float", '{"a": 0.0}', {"a": 0.0}),
    ("exponent_float", "[1e5, 1E5, 1e+5, 1.5E-3, -2e2, 0e0]", [1e5, 1e5, 1e5, 1.5e-3, -2e2, 0.0]),
    ("fraction_float", "[1.0, 10.50, 0.1]", [1.0, 10.5, 0.1]),
    ("integer", "[10, 0, -7]", [10, 0, -7]),
    (
        "yaml_resolvable_strings",
        '["2026-07-11", "2001-12-14 21:59:43", "yes", "no", "on", "null", "~", "true",'
        ' "1e5", "0x10", ".inf", ".nan", "<<", "---", "&a", "*a", "!t", "#c", "a: b"]',
        [
            "2026-07-11",
            "2001-12-14 21:59:43",
            "yes",
            "no",
            "on",
            "null",
            "~",
            "true",
            "1e5",
            "0x10",
            ".inf",
            ".nan",
            "<<",
            "---",
            "&a",
            "*a",
            "!t",
            "#c",
            "a: b",
        ],
    ),
    ("merge_value_is_not_a_key", '{"a": "<<"}', {"a": "<<"}),
    ("escapes", r'["\/", "\b\f\n\r\t", "\u0000", "\"", "\\", "\u00e9", "\u2028"]', AS_JSON),
    ("raw_astral", '{"a": "\U0001f600"}', {"a": "\U0001f600"}),
    ("raw_bom_inside_string", '{"a": "x\ufeffy"}', {"a": "x\ufeffy"}),
    ("raw_line_separator", '{"a": "x\u2028y"}', {"a": "x\u2028y"}),
    # A raw NEL is a YAML line break, so ruamel folds it; JSON would keep it.
    ("raw_next_line_folds", '{"a": "x\x85y"}', {"a": "x y"}),
    ("bom", '\ufeff{"a": 1}', {"a": 1}),
    ("trailing_newline", '{"a": 1}\n', {"a": 1}),
    ("trailing_whitespace", '{"a": 1}   \n\n  ', {"a": 1}),
    ("leading_whitespace", '  \n {"a": 1}', {"a": 1}),
    ("empty", "", None),
    ("whitespace_only", "  \n", None),
    ("empty_key", '{"": 1}', {"": 1}),
    ("empty_collections", "[[], {}, [[]]]", [[], {}, [[]]]),
    ("key_of_1022_characters", '{"' + "k" * 1022 + '": 1}', {"k" * 1022: 1}),
    # A key's raw extent, escapes included, is what YAML limits to 1024 characters.
    ("escaped_key_within_raw_limit", '{"' + r"\u0041" * 128 + '": 1}', {"A" * 128: 1}),
    ("long_value", '{"a": "' + "v" * 5000 + '"}', {"a": "v" * 5000}),
    ("top_level_string", '"hello"', "hello"),
    ("top_level_number", "1e5", 1e5),
    ("depth_at_limit", _nest(MAX_DEPTH), AS_JSON),
    # Flow-style YAML that is not strict JSON keeps its YAML meaning.
    ("flow_plain_scalars", "{a: 1, b: [x, y]}", {"a": 1, "b": ["x", "y"]}),
    ("flow_trailing_comma", '{"a": 1,}', {"a": 1}),
    ("flow_single_quotes", "['a', 'b']", ["a", "b"]),
    ("flow_comment", '{"a": 1} # note', {"a": 1}),
    ("flow_unquoted_date", '{"a": 2026-07-11}', {"a": "2026-07-11"}),
]


@pytest.mark.parametrize(
    ("text", "expected"), [c[1:] for c in VALUE_CASES], ids=[c[0] for c in VALUE_CASES]
)
def test_pinned_value(text: str, expected: Any) -> None:
    value = parse_yaml(text)
    if expected is AS_JSON:
        expected = json.loads(text)
    assert _same(value, expected), (value, expected)


ERROR_CASES: list[tuple[str, str, str]] = [
    ("duplicate_key", '{"a": 1, "a": 2}', "yaml_duplicate_key"),
    ("nested_duplicate_key", '{"a": [{"b": 1, "c": 2, "b": 3}]}', "yaml_duplicate_key"),
    ("merge_key", '{"<<": {"a": 1}}', "yaml_merge_key"),
    ("unsafe_integer", '{"a": 9007199254740992}', "number_out_of_range"),
    ("unsafe_negative_integer", "[-9007199254740992]", "number_out_of_range"),
    ("huge_integer", "[" + "9" * 5000 + "]", "yaml_parse_error"),
    ("overflowing_float", "[1e400]", "number_out_of_range"),
    ("negative_zero_float", '{"a": -0.0}', "number_negative_zero"),
    ("negative_zero_exponent", "[-0e0]", "number_negative_zero"),
    ("lone_surrogate_escape", r'{"a": "\ud800"}', "yaml_unsupported_scalar"),
    # ruamel decodes each half of an escaped surrogate pair on its own, so the pair
    # is two lone surrogates. ``json`` would join it into one valid character.
    ("surrogate_pair_escape", r'{"a": "\ud83d\ude00"}', "yaml_unsupported_scalar"),
    ("raw_lone_surrogate", '{"a": "\ud800"}', "yaml_parse_error"),
    ("depth_over_limit", _nest(MAX_DEPTH + 1), "yaml_limit"),
    ("hostile_depth", "[" * 50_000 + "]" * 50_000, "yaml_limit"),
    ("leading_tab", '\t{"a": 1}', "yaml_parse_error"),
    ("trailing_tab", '{"a": 1}\t', "yaml_parse_error"),
    ("tab_on_trailing_line", '{"a": 1}\n\t\n', "yaml_parse_error"),
    ("newline_before_colon", '{"a"\n: 1}', "yaml_parse_error"),
    ("carriage_return_before_colon", '{"a"\r: 1}', "yaml_parse_error"),
    ("key_of_1023_characters", '{"' + "k" * 1023 + '": 1}', "yaml_parse_error"),
    ("escaped_key_over_raw_limit", '{"' + r"\u0041" * 171 + '": 1}', "yaml_parse_error"),
    ("long_gap_before_colon", '{"a"' + " " * 1100 + ": 1}", "yaml_parse_error"),
    ("raw_delete", '{"a": "\x7f"}', "yaml_parse_error"),
    ("raw_c1_control", '{"a": "\x80"}', "yaml_parse_error"),
    ("raw_noncharacter", '{"a": "\ufffe"}', "yaml_parse_error"),
    ("multiple_documents", '{"a": 1}\n---\n{"b": 2}', "yaml_parse_error"),
    ("flow_infinity", '{"a": .inf}', "number_out_of_range"),
]


PURE_RUAMEL_ONLY = {"lone_surrogate_escape", "surrogate_pair_escape", "trailing_tab"}
"""Pinned errors that describe pure ruamel only.

libyaml refuses an escaped surrogate outright, joins an escaped pair into one character,
and accepts a trailing tab, so with the C extension installed these three read differently.
"""


@pytest.mark.parametrize(
    ("text", "code"),
    [
        pytest.param(
            *case[1:], id=case[0], marks=[pure_ruamel_only] if case[0] in PURE_RUAMEL_ONLY else []
        )
        for case in ERROR_CASES
    ],
)
def test_pinned_error(text: str, code: str) -> None:
    with pytest.raises(PortableInputError) as raised:
        parse_yaml(text)
    assert raised.value.code == code


PINNED = VALUE_CASES + ERROR_CASES


@pytest.mark.parametrize("text", [c[1] for c in PINNED], ids=[c[0] for c in PINNED])
def test_pinned_inputs_parse_identically(text: str) -> None:
    _assert_equivalent(text)


# --- Equivalence over a corpus -----------------------------------------------------------


def _repo_files(*suffixes: str) -> list[Path]:
    """The tracked files with one of ``suffixes``, so the corpus is the same in every checkout.

    A walk of the working tree would also read ignored and untracked files, whose number
    and content differ from one checkout to the next.
    """
    try:
        listed = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--", *(f"*{s}" for s in suffixes)],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover
        pytest.skip("the repo corpus needs a git checkout")
    paths = [REPO_ROOT / name for name in listed.decode("utf-8").split("\0") if name]
    return [path for path in paths if path.is_file()]


def test_every_repo_json_file_parses_identically() -> None:
    paths = _repo_files(".json")
    assert paths, "the corpus found no JSON files"
    for path in paths:
        _assert_equivalent(path.read_text(encoding="utf-8"))


def _repo_yaml_texts() -> Iterator[str]:
    """Every YAML document in the repo: whole YAML files and Markdown frontmatter."""
    for path in _repo_files(".yaml", ".yml"):
        yield path.read_text(encoding="utf-8")
    for path in _repo_files(".md"):
        split = _portable.split_frontmatter(path.read_text(encoding="utf-8"))
        if split is not None:
            yield split.metadata_text


JSON_SPELLINGS: list[Callable[[Any], str]] = [
    json.dumps,
    lambda value: json.dumps(value, indent=2),
    lambda value: json.dumps(value, indent="\t"),
    lambda value: json.dumps(value, separators=(",", ":")),
    lambda value: json.dumps(value, ensure_ascii=False, indent=1),
]


@slow
@requires_json_path
def test_repo_yaml_documents_respelled_as_json_parse_identically() -> None:
    """Every parseable YAML document in the repo, in each common JSON spelling."""
    fast = total = 0
    for text in _repo_yaml_texts():
        _assert_equivalent(text)
        try:
            value = _ruamel_path(text)
        except PortableInputError:
            continue
        for spell in JSON_SPELLINGS:
            total += 1
            fast += _assert_equivalent(spell(value))
    # A respelling only falls back for an escaped surrogate or a scalar root.
    assert fast * 10 >= total * 8, f"only {fast} of {total} respelled documents took the JSON path"


_SAFE_KEYS = ["a", "name", "", "\u00e9", "date", "yes", "x y", "a: b", "#", "\U0001f600"]
_HOSTILE_KEYS = ["<<", "k" * 200, "k" * 1030]
_SAFE_STRINGS = [
    "plain",
    "",
    " padded ",
    "2026-07-11",
    "12:30:00",
    "yes",
    "off",
    "~",
    "null",
    "NaN",
    ".inf",
    "0x1F",
    "1e5",
    "---",
    "...",
    "- item",
    "#hash",
    "&anchor",
    "*alias",
    "!tag",
    "%dir",
    "@",
    "`",
    'quote " back \\ slash / solidus',
    "line\nbreak\ttab\rreturn\bback\fform",
    "\x00\x01\x1f\x7f\x85\u2028\u2029\ufffe",  # escaped, or raw past C0 when not ASCII
    "\u00e9 \u00fc \u00df",
    "\u4e2d\u6587",
    "\U0001f600",
    "\xa0nbsp",
    "\ufeffbom",
    "v" * 1500,
]
_HOSTILE_STRINGS = ["\x85", "\x7f", "\ufffe", "\u2028\u2029", "x\x9fy"]
_NUMBERS = [
    "0",
    "-0",
    "7",
    "-12",
    "9007199254740991",
    "9007199254740992",
    "-9007199254740993",
    "1.0",
    "-0.0",
    "0.5",
    "10.50",
    "1e5",
    "1E5",
    "1e+5",
    "1.5e-3",
    "-2E+2",
    "0e0",
    "-0e0",
    "1e400",
    "-1e400",
    "5e-324",
    "1.7976931348623157e308",
    "123456789012345678901234567890",
    "0.30000000000000004",
]
_SAFE_LITERALS = ["true", "false", "null"]
_HOSTILE_LITERALS = ["NaN", "Infinity", "-Infinity"]
_GAPS = ["", " ", "\n", "\n  ", "\t", "\r\n", "  \n\t "]
_SURROGATE_PAIR_ESCAPE = json.dumps("\U0001f600")[1:-1]


class _Generator:
    """JSON-shaped texts; hostile ones also use every shape YAML reads differently."""

    def __init__(self, rng: random.Random, *, hostile: bool) -> None:
        self.rng = rng
        self.hostile = hostile

    def _pick(self, safe: list[str], hostile: list[str]) -> str:
        if self.hostile and self.rng.random() < 0.15:
            return self.rng.choice(hostile)
        return self.rng.choice(safe)

    def document(self) -> str:
        return self.collection(0)

    def collection(self, depth: int) -> str:
        rng = self.rng
        if rng.random() < 0.5:
            keys = [self._pick(_SAFE_KEYS, _HOSTILE_KEYS) for _ in range(rng.randrange(5))]
            if not (self.hostile and rng.random() < 0.2):
                keys = list(dict.fromkeys(keys))
            entries = [
                self.gap()
                + self.string(key)
                + self.colon_gap()
                + ":"
                + self.gap()
                + self.value(depth + 1)
                + self.gap()
                for key in keys
            ]
            return "{" + ",".join(entries) + "}"
        items = [self.gap() + self.value(depth + 1) + self.gap() for _ in range(rng.randrange(5))]
        return "[" + ",".join(items) + "]"

    def value(self, depth: int) -> str:
        roll = self.rng.random()
        if depth < 6 and roll < 0.35:
            return self.collection(depth)
        if roll < 0.65:
            return self.string(self._pick(_SAFE_STRINGS, _HOSTILE_STRINGS))
        if roll < 0.9:
            return self.rng.choice(_NUMBERS)
        return self._pick(_SAFE_LITERALS, _HOSTILE_LITERALS)

    def gap(self) -> str:
        return self.rng.choice(_GAPS) if self.rng.random() < 0.4 else ""

    def colon_gap(self) -> str:
        roll = self.rng.random()
        if self.hostile and roll < 0.03:
            return self.rng.choice(["\n", "\r\n ", " " * 1100])
        return " " if roll < 0.2 else ""

    def string(self, value: str) -> str:
        text = json.dumps(value, ensure_ascii=self.rng.random() < 0.5)
        if self.hostile and self.rng.random() < 0.03:
            text = text[:-1] + _SURROGATE_PAIR_ESCAPE + '"'
        return text


@slow
@requires_json_path
def test_generated_documents_parse_identically() -> None:
    rng = random.Random(20261024)
    fast = slow = 0
    for index in range(4000):
        hostile = index % 2 == 1
        text = _Generator(rng, hostile=hostile).document()
        if hostile and rng.random() < 0.2:
            text = rng.choice(["", " \n", "\t", "\ufeff"]) + text + rng.choice(["", "\n", "\t"])
        elif rng.random() < 0.1:
            text = rng.choice(["", " ", "\n"]) + text + rng.choice(["", "\n", " \r\n"])
        if _assert_equivalent(text):
            fast += 1
        else:
            slow += 1
    # Both branches must run often for the comparison to mean anything.
    assert fast > 2000, fast
    assert slow > 500, slow


@slow
def test_generated_deep_documents_parse_identically() -> None:
    for depth in (1, MAX_DEPTH - 1, MAX_DEPTH, MAX_DEPTH + 1, 2 * MAX_DEPTH, 600):
        _assert_equivalent(_nest(depth))
        _assert_equivalent("[" * depth + "]" * depth)
        _assert_equivalent('{"value": ' + "[" * depth + "0" + "]" * depth + "}")


SAMPLED_CODE_POINTS = [
    *range(0x400),
    *range(0x2000, 0x2070),
    *range(0xD7F0, 0xE010),
    *range(0xFDD0, 0xFDF0),
    *range(0xFEF0, 0x10000),
    0x10000,
    0x1F600,
    0x10FFFF,
]


@slow
@pytest.mark.parametrize(
    "template", ['{{"k": "{c}"}}', '{{"{c}": 1}}', '["a{c}b"]', "[1,{c}2]", '{{"k"{c}: 1}}']
)
def test_each_sampled_character_parses_identically(template: str) -> None:
    for code in SAMPLED_CODE_POINTS:
        _assert_equivalent(template.format(c=chr(code)))


@slow
def test_raw_character_guard_covers_every_character_ruamel_rejects() -> None:
    """Exhaustive over Unicode: ruamel's unreadable characters and line breaks fall back.

    The JSON path skips ruamel's reader, so every raw character that reader refuses, and
    every character ruamel treats as a line break, which changes where a key ends and how
    a quoted scalar folds, must be refused by strict ``json`` itself or by the guard.
    JSON whitespace is the exception: ruamel skips it between flow tokens too.
    """
    line_breaks = {"\n", "\r", "\x85", "\u2028", "\u2029"}
    json_whitespace = {" ", "\t", "\n", "\r"}

    def json_refuses(char: str) -> bool:
        try:
            json.loads(f'"{char}"')
        except ValueError:
            return True
        return False

    for code in range(0x110000):
        char = chr(code)
        refused = Reader.NON_PRINTABLE.match(char) is not None or char in line_breaks
        if refused and char not in json_whitespace:
            assert _portable._json_has_unsafe_character(char) or json_refuses(char), hex(code)


# --- Which path runs -----------------------------------------------------------------------


class _RuamelCalled(AssertionError):
    pass


def _forbid_ruamel(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise _RuamelCalled

    monkeypatch.setattr(_portable, "YAML", refuse)


@requires_json_path
def test_plain_json_document_never_reaches_ruamel(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_ruamel(monkeypatch)
    text = '{"text": "hello", "count": 42, "ratio": 1.5, "items": [true, null, {"k": "v"}]}'
    assert parse_yaml(text) == json.loads(text)


@requires_json_path
def test_json_artifact_file_never_reaches_ruamel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps({"softschema": {"contract": "example:Doc/v1"}, "a": [1]}, indent=2))
    _forbid_ruamel(monkeypatch)
    assert read_yaml_doc(path) == {"softschema": {"contract": "example:Doc/v1"}, "a": [1]}


@requires_json_path
def test_portable_value_errors_in_json_documents_never_reach_ruamel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_ruamel(monkeypatch)
    for text, code in [
        ('{"a": 9007199254740992}', "number_out_of_range"),
        ('{"a": -0.0}', "number_negative_zero"),
        ("[1e400]", "number_out_of_range"),
    ]:
        with pytest.raises(PortableInputError) as raised:
            parse_yaml(text)
        assert raised.value.code == code


@pytest.mark.parametrize(
    "text",
    [
        '{"a": 1, "a": 2}',
        '{"<<": 1}',
        '{"a": NaN}',
        '{"a": Infinity}',
        r'{"a": "\ud83d\ude00"}',
        '{"a": "\x7f"}',
        '{"a": "x\x85y"}',
        '{"a": "x\u2028y"}',
        '\t{"a": 1}',
        '{"a": 1}\t',
        '{"a"\n: 1}',
        '{"' + "k" * 200 + '": 1}',
        '{"a"' + " " * 200 + ": 1}",
        _nest(MAX_DEPTH + 1),
        "[" + "9" * 5000 + "]",
        "{a: 1}",
        "",
    ],
)
def test_every_disagreement_shape_takes_the_ruamel_path(text: str) -> None:
    assert _portable._parse_json_subset(text) is _portable._NOT_JSON


def test_c_parser_keeps_every_text_on_the_ruamel_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_portable, "_JSON_PATH_ENABLED", False)
    assert _portable._parse_json_subset('{"a": [1, 2.5, "x"]}') is _portable._NOT_JSON


@pytest.mark.parametrize(
    ("version", "checked"),
    [
        ((0, 17, 40), False),
        ((0, 18, 0), True),
        ((0, 18, 17), True),
        ((0, 19, 1), True),
        ((0, 20, 0), False),
        ((1, 0, 0), False),
    ],
)
def test_json_path_is_gated_to_the_checked_ruamel_releases(
    version: tuple[int, ...], checked: bool
) -> None:
    """A ruamel release the guards were not derived from keeps every text on ruamel."""
    assert _portable._ruamel_is_checked(version) is checked


def test_installed_ruamel_is_a_checked_release() -> None:
    """The locked ruamel is inside the range, so this suite exercises the JSON path."""
    assert _portable._ruamel_is_checked(), ruamel.yaml.version_info
