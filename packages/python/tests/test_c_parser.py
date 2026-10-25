"""With ruamel's C extension installed, ``parse_yaml`` still reads every text as pure ruamel.

``ruamel.yaml.clib`` replaces ruamel's reader, scanner and parser with libyaml, a YAML 1.1
scanner. Construction and resolution stay in Python, so on ordinary documents the two
agree, but libyaml rejects some texts pure ruamel reads, accepts some it rejects, reads a
few differently, and words most errors differently. ``parse_yaml`` therefore
tries the C parser first only on texts with none of the shapes where the two disagree,
and re-reads with pure ruamel on any failure, so pure ruamel stays the definition.

These tests compare three readings of each text:

- **C-first**: ``parse_yaml`` as it runs with the extension, the default once installed;
- **forced**: ``parse_yaml`` with ``SOFTSCHEMA_PURE_YAML=1``;
- **reference**: ``parse_yaml`` in a fresh interpreter that cannot import the extension,
  which is softschema exactly as it behaves without it.

All three must agree on the value (type, key order, float bits) or on the error code and
message. Without the extension there is no C parser to compare, and those tests skip.
"""

from __future__ import annotations

import io
import json
import math
import os
import pickle
import random
import re
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.parser import Parser as RuamelParser

import softschema
from softschema import _portable
from softschema._portable import PortableInputError, parse_yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
PURE_ENV = "SOFTSCHEMA_PURE_YAML"

C_AVAILABLE = YAML(typ="safe").Parser is not RuamelParser
requires_c = pytest.mark.skipif(
    not C_AVAILABLE,
    reason="ruamel.yaml.clib is not installed, so there is no C parser to compare",
)

Outcome = tuple[Any, ...]


def _outcome(text: str) -> Outcome:
    try:
        return ("value", parse_yaml(text))
    except PortableInputError as exc:
        return ("error", exc.code, str(exc))
    except Exception as exc:
        return ("exception", type(exc).__name__, str(exc))


# A fresh interpreter in which ``import _ruamel_yaml`` fails, so ruamel falls back to its
# pure-Python parser exactly as it does when the extension is not installed.
_REFERENCE_PROGRAM = """
import pickle, sys
sys.modules["_ruamel_yaml"] = None
from ruamel.yaml import YAML
from ruamel.yaml.parser import Parser
assert YAML(typ="safe").Parser is Parser, "the C parser is still importable"
from softschema._portable import PortableInputError, parse_yaml
request = pickle.load(sys.stdin.buffer)
if request == "mode":
    from softschema import yaml_parser_mode
    pickle.dump(yaml_parser_mode(), sys.stdout.buffer)
    raise SystemExit
if request == "reason":
    from softschema._portable import yaml_parser_reason
    pickle.dump(yaml_parser_reason(), sys.stdout.buffer)
    raise SystemExit
if request == "compile":
    from softschema.compile import _yaml_dump
    from tests_c_parser_schema import SCHEMA
    pickle.dump(_yaml_dump(SCHEMA), sys.stdout.buffer)
    raise SystemExit
outcomes = []
for text in request:
    try:
        outcomes.append(("value", parse_yaml(text)))
    except PortableInputError as exc:
        outcomes.append(("error", exc.code, str(exc)))
    except Exception as exc:
        outcomes.append(("exception", type(exc).__name__, str(exc)))
pickle.dump(outcomes, sys.stdout.buffer)
"""


def _in_reference_process(request: Any, extra_path: Path | None = None) -> Any:
    env = {key: value for key, value in os.environ.items() if key != PURE_ENV}
    if extra_path is not None:
        env["PYTHONPATH"] = os.pathsep.join([str(extra_path), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", _REFERENCE_PROGRAM],
        input=pickle.dumps(request),
        capture_output=True,
        env=env,
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    return pickle.loads(result.stdout)


def _same(left: Any, right: Any) -> bool:
    """Equal in type, key order, and float bits, which ``==`` does not check."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(_same(left[key], right[key]) for key in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(map(_same, left, right))
    if isinstance(left, float):
        return left.hex() == right.hex() or (math.isnan(left) and math.isnan(right))
    return left == right


def _assert_reads_as_pure(texts: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """C-first, forced-pure and reference readings agree on every text."""
    reference = _in_reference_process(texts)
    monkeypatch.delenv(PURE_ENV, raising=False)
    c_first = [_outcome(text) for text in texts]
    monkeypatch.setenv(PURE_ENV, "1")
    forced = [_outcome(text) for text in texts]
    mismatches = [
        (text[:120], ref, c, f)
        for text, ref, c, f in zip(texts, reference, c_first, forced, strict=True)
        if not (_same(ref, c) and _same(ref, f))
    ]
    assert not mismatches, f"{len(mismatches)} of {len(texts)} differ, first: {mismatches[:5]}"


# --- Inputs on which libyaml and pure ruamel disagree ---------------------------------

EDGE_CASES: dict[str, str] = {
    # A plain scalar with a colon inside a flow collection is YAML 1.2, not 1.1.
    "flow_seq_https_url": "sources: [https://example.com/a?b=c]\n",
    "flow_map_https_url": "m: {url: https://example.com/a}\n",
    "flow_seq_times": "t: [10:30, 11:00]\n",
    "plain_colon_in_flow": "{a: b:c}\n",
    "url_in_flow": "[http://x.y/z]\n",
    "flow_seq_spaced_colon": "[a :1]",
    "flow_map_spaced_colon": "{a :b}",
    "flow_seq_quoted_url": 'sources: ["https://example.com/a"]\n',
    "flow_single_pair": "a: [x: 1]\n",
    # libyaml reads ':' after a quoted key in a flow sequence as an indicator.
    "flow_seq_quoted_key_adjacent_colon": '["a":1]',
    "flow_seq_single_quoted_key_adjacent_colon": "['a':b]",
    "flow_seq_quoted_key_spaced_colon": '["k"  :v]',
    "flow_seq_quoted_key_colon_no_value": '["":]',
    "flow_seq_nested_quoted_key": 'x: [a, "k":v]\n',
    "flow_seq_explicit_key_adjacent_colon": '[? "a":1]',
    # ... and after an explicit key, a colon on a later line or after a comment.
    "flow_seq_explicit_key_colon_next_line": '[? "a"\n:x]',
    "flow_seq_explicit_key_colon_after_comment": '[? "a" # c\n:x]',
    "flow_seq_explicit_plain_key_colon_after_comment": "[? a #c\n:x]",
    "flow_seq_explicit_key_colon_indented": "a: [? 'k'\n  :v]\n",
    "flow_seq_explicit_key_empty_value": '[?""\n:]',
    "flow_seq_explicit_key_spaced_colon_space": '[? "a"\n: x]',
    "flow_seq_explicit_plain_key_next_line": "[? a\n:x]",
    "flow_map_explicit_key_colon_next_line": '{? "a"\n:x}',
    # Document end markers: libyaml skips a second one, pure ruamel rejects it.
    "repeated_document_end": "a: 1\n...\n...\n",
    "repeated_document_end_after_comment": "a: 1\n...\n# c\n...\n",
    "repeated_document_end_after_block_scalar": "a: |\n  x\n...\n...\n",
    "repeated_document_end_after_marker": "---\n...\n...\n",
    "document_end_with_comment": "a: 1\n... # c\n",
    "ellipsis_in_value": "a: and so on...\nb: ...\n",
    # Tabs: libyaml skips a tab between block tokens where pure ruamel refuses it.
    "trailing_tab_after_root": '{"a": 1}\t\n',
    "tab_before_root": '\t{"a": 1}\n',
    "tab_after_quoted_value": 'a: "x"\t\n',
    "tab_after_plain_value": "a: b\t\n",
    "tab_after_colon": "a:\tb\n",
    "tab_after_flow_value": "a: [1]\t\n",
    "tab_before_colon": '"a"\t: 1\n',
    "tab_after_document_start": "---\tx\n",
    "tab_after_dash": '- "x"\t\n',
    "tab_before_comment": "a: 1\t# c\n",
    "tab_indent": "a:\n\tb: 1\n",
    "tab_in_quoted": 'a: "x\ty"\n',
    "tab_in_block_scalar": "a: |\n  x\ty\n",
    # A byte order mark: libyaml skips one at the start of any line.
    "bom_at_line_start": "a: 1\n\ufeffb: 2\n",
    "bom_inside": "a: \ufeffx\n",
    "bom_leading": "\ufeffa: 1\n",
    "bom_before_directive": "\ufeff%YAML 1.1\n---\na: yes\n",
    # NEL, LS and PS: line breaks to both scanners, which still fold them differently.
    "nel_in_plain": "a: x\u0085y\n",
    "nel_in_quoted": 'a: "x\u0085y"\n',
    "ls_in_plain": "a: x\u2028y\n",
    "ls_in_dq": 'a: "x\u2028y"\n',
    "ps_in_plain": "a: x\u2029y\n",
    "nel_line_breaks": "a: 1\u0085b: 2\u0085",
    # Directives: libyaml ignores %YAML 1.1 when values are resolved.
    "yaml11_directive_bools": "%YAML 1.1\n---\na: yes\nb: on\nc: 0o17\nd: 017\n",
    "yaml12_directive": "%YAML 1.2\n---\na: yes\n",
    "reserved_directive": "%FOO bar\n---\na: 1\n",
    "tag_directive": "%TAG !e! tag:example.com,2000:\n---\na: 1\n",
    "directive_after_cr": "a: 1\r%YAML 1.1\r---\rb: 2\r",
    # Block scalars.
    "block_header_comment_without_space": "a: |#c\n  x\n",
    "folded_header_comment_without_space": "a: >-#c\n  x\n",
    "root_block_scalar_column_zero_hash": "|\n#x\n",
    "root_block_scalar_after_marker": "--- |\n#x\n",
    "root_block_scalar_after_comment": "# c\n>\n#x\n",
    "root_block_scalar_after_banner": "#" * 40 + "\n# Title\n" + "#" * 40 + "\n|\n#x\n",
    "comment_containing_pipe": "# |\na: 1\n",
    "comment_containing_gt": "#>\na: 1\n",
    "comment_containing_pipe_text": "# x | y\na: 1\n",
    "banner_comment": "#" * 40 + "\n# Movie page record\n" + "#" * 40 + "\ntitle: x\n",
    "block_scalar_short_space_line": "a: |\n \n  x\n",
    "block_scalar_short_space_line_folded": "a: >\n  \n   x\n",
    "block_scalar_space_line_with_indicator": "a: |2\n \n   x\n",
    "block_scalar_empty_first_line": "a: |\n\n \n  x\n",
    "block_scalar_keep": "a: |+\n  x\n\n\nb: 1\n",
    "folded": "a: >\n  x\n  y\n\n  z\n",
    "nested_block_scalar_hash": "a: |\n  #x\n",
    # Escapes: libyaml refuses escaped surrogates, pure ruamel decodes each half.
    "lone_surrogate_escape": 'a: "\\ud800"\n',
    "surrogate_pair_escape": 'a: "\\ud83d\\ude00"\n',
    "quoted_escapes": 'a: "\\x41\\u00e9\\U0001F600\\t\\N\\_\\L\\P"\n',
    "solidus_escape": 'a: "\\/"\n',
    "invalid_escape": 'a: "\\q"\n',
    "raw_lone_surrogate": "a: \ud800\n",
    # Errors both reject, where libyaml words the message differently.
    "duplicate_key": "a: 1\na: 2\n",
    "bad_indent": "a:\n  b: 1\n c: 2\n",
    "unterminated_dq": 'a: "abc\n',
    "unterminated_sq": "a: 'abc\n",
    "nul_char": "a: x\x00y\n",
    "del_char": "a: x\x7fy\n",
    "c1_char": "a: x\x9fy\n",
    "long_key_1100": "k" * 1100 + ": 1\n",
    "flow_long_key": '{"' + "k" * 1100 + '": 1}\n',
    "key_colon_newline_flow": '{"a"\n: 1}\n',
    "multi_doc": "a: 1\n---\nb: 2\n",
    "non_string_key": "1: a\ntrue: b\n",
    "percent_plain": "a: %x\n",
    "backtick": "a: `x`\n",
    "at_sign": "a: @x\n",
    "deep_nesting": "[" * 70 + "]" * 70,
    "content_after_document_end": "a: 1\n... b\n",
    # Rejected by the preflight on both paths.
    "alias": "a: &x 1\nb: *x\n",
    "anchor_only": "a: &x 1\n",
    "explicit_tag": "a: !!str 1\n",
    "custom_tag": "a: !foo 1\n",
    "merge_key": "a: {x: 1}\nb:\n  <<: {y: 2}\n",
    # Ordinary documents, which both read alike.
    "yaml12_bools": "a: yes\nb: on\nc: true\nd: 0o17\ne: 017\n",
    "timestamp": "a: 2026-10-24\nb: 2026-10-24T10:00:00Z\n",
    "floats": "a: 1e3\nb: .5\nc: 1_000\nd: .inf\ne: -.NaN\n",
    "big_int": "a: 9007199254740993\n",
    "neg_zero": "a: -0.0\n",
    "astral_raw": "a: \U0001f600\n",
    "unicode_key": "\u00e9: 1\n",
    "single_quote_escape": "a: 'it''s'\n",
    "complex_key": "? [a, b]\n: 1\n",
    "comment_after_value": "a: 1 # c\nb: 'x' #c\n",
    "comment_after_quoted_without_space": 'a: "x"#c\n',
    "crlf": "a: 1\r\nb:\r\n  - x\r\n",
    "cr_only": "a: 1\rb: 2\r",
    "indented_seq": "a:\n- 1\n- 2\n",
    "dash_no_space": "a:\n  -1\n",
    "question_plain": "a: ?x\n",
    "doc_end_marker": "a: 1\n...\n",
    "empty": "",
    "only_comment": "# c\n",
    "null_root": "null\n",
    "scalar_root": "hello\n",
    "very_long_line": "a: " + "x" * 200_000 + "\n",
    "block_url": "a: https://example.com/a\n",
    "block_seq_url": "a:\n  - https://example.com/a\n",
}


@requires_c
def test_edge_cases_read_as_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    _assert_reads_as_pure(list(EDGE_CASES.values()), monkeypatch)


# --- Corpus: the repo's own documents and the shared vectors ---------------------------


def _repo_files(*suffixes: str) -> list[Path]:
    """The tracked files with one of ``suffixes``, so the corpus is the same in every checkout."""
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


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(key)
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _repo_texts() -> list[str]:
    """Every repo YAML/JSON file and frontmatter block, and every string in the vectors."""
    texts = [path.read_text(encoding="utf-8") for path in _repo_files(".yaml", ".yml", ".json")]
    for path in _repo_files(".md"):
        split = _portable.split_frontmatter(path.read_text(encoding="utf-8"))
        if split is not None:
            texts.append(split.metadata_text)
    for path in sorted((REPO_ROOT / "tests/vectors").glob("*.yaml")):
        texts.extend(_strings(YAML(typ="safe", pure=True).load(path.read_text(encoding="utf-8"))))
    return list(dict.fromkeys(texts))


@requires_c
def test_repo_documents_and_vector_texts_read_as_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    texts = _repo_texts()
    assert len(texts) > 200, len(texts)
    _assert_reads_as_pure(texts, monkeypatch)


# --- Generated corpus ---------------------------------------------------------------------

ALPHABET = [
    "a", " ", "\t", "\n", ":", "-", "#", '"', "'", "[", "]", "{", "}", ",", "?", "\\",
    "\ufeff", "\x85", "%", "|", ">", "!", "&", "*", "\r", "1", ".", "\u2028",
]  # fmt: skip
TEMPLATES = [
    "{s}", "a: {s}\n", "- {s}\n", "[{s}]", "{{{s}}}", "a:\n  {s}\n", '"{s}"', "a: '{s}'\n",
    "a: |\n  {s}\n", "a: >\n  x\n  {s}\n", "{s}\nb: 1\n", "a: 1\n{s}", "- [x, {s}]\n",
    "a: {{b: {s}}}\n", '{{"a": {s}}}', "--- {s}\n", "a: x\n  {s}\n", "? {s}\n: 1\n",
    '["k"{s}]', "|\n{s}\n",
]  # fmt: skip
PAIR_TEMPLATES = ["{s}", "a: {s}\n", "[{s}]", "{{{s}}}", '["k"{s}]', "|\n{s}\n", "a: |\n  {s}\n"]


def _short_texts() -> list[str]:
    """Every string of up to one alphabet character in each template, and of two in some.

    The offline search behind the guards went to four characters bare and three in each
    template; this keeps the unit run to a few seconds.
    """
    singles = [template.format(s=piece) for piece in ["", *ALPHABET] for template in TEMPLATES]
    pairs = [a + b for a in ALPHABET for b in ALPHABET]
    return singles + [template.format(s=pair) for pair in pairs for template in PAIR_TEMPLATES]


@requires_c
def test_generated_short_texts_read_as_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    _assert_reads_as_pure(_short_texts(), monkeypatch)


SCALARS = [
    "x", "hello world", "a:b", "a #b", "-x", "?x", ":x", "x:", "http://e.com/a?b=c", "10:30",
    "2026-10-24", "yes", "on", "~", "null", "1e3", "0o17", "017", "0x1F", ".inf", "1_000",
    "+1", "-0", "-0.0", "\u00e9", "\u4e2d\u6587", "\U0001f600", "tab\there", "nel\x85x",
    "ls\u2028x", "bom\ufeffx", "back\\slash", 'quote"d', "it's", "multi\nline",
    "multi\n\nblank", "trail ", " lead", "%pct", "@at", "&and", "*ali", "!tag", "|pipe",
    ">gt", "[br]", "{cb}", "a,b", "", " ", "k" * 1030,
]  # fmt: skip


class _Generator:
    """Seeded block and flow documents that mix every shape the scanners disagree on."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def scalar(self, flow: bool, indent: int) -> str:
        rng = self.rng
        text = rng.choice(SCALARS)
        style = rng.choice(["plain", "plain", "single", "double", "double", "literal", "folded"])
        if flow and style in ("literal", "folded"):
            style = "double"
        if style == "plain":
            return text.replace("\n", "\n" + " " * (indent + 2))
        if style == "single":
            return "'" + text.replace("'", "''").replace("\n", "\n" + " " * (indent + 1)) + "'"
        if style == "double":
            body = text.replace("\\", "\\\\").replace('"', '\\"')
            body = body.replace("\n", "\\n" if rng.random() < 0.3 else "\n" + " " * (indent + 1))
            if rng.random() < 0.2:
                body += rng.choice(["\\t", "\\/", "\\x41", "\\u00e9", "\\U0001F600", "\\N", "\\_"])
            return '"' + body + '"'
        header = rng.choice(["|", ">", "|-", ">+", "|2", ">-", "|+", "|#", "| #c"])
        pad = " " * (indent + 2)
        lines = text.split("\n")
        lead = rng.choice(["", "", "\n", " \n", pad + "\n"])
        return header + "\n" + lead + "\n".join(pad + line if line else "" for line in lines)

    def flow(self, depth: int) -> str:
        rng = self.rng
        if rng.random() < 0.5:
            items = [self.flow_node(depth + 1) for _ in range(rng.randrange(4))]
            if rng.random() < 0.3:
                items.append(self.scalar(True, 0) + rng.choice([":", ": ", " :", ":x", " : "]))
            return "[" + rng.choice([", ", ",", ",\n  "]).join(items) + "]"
        pairs = [
            self.scalar(True, 0) + rng.choice([": ", ":", " : ", " :"]) + self.flow_node(depth + 1)
            for _ in range(rng.randrange(4))
        ]
        return "{" + rng.choice([", ", ","]).join(pairs) + "}"

    def flow_node(self, depth: int) -> str:
        if depth < 3 and self.rng.random() < 0.3:
            return self.flow(depth)
        return self.scalar(True, 0)

    def block(self, indent: int, depth: int) -> str:
        rng = self.rng
        pad = " " * indent
        lines = []
        if rng.random() < 0.6:
            for _ in range(rng.randrange(1, 4)):
                key = rng.choice(["a", "b", "key", "x y", '"q"', "'s'", "\u00e9", "k" * 1020])
                sep = rng.choice([":", ":", " :", ":\t", "\t:"])
                if depth < 3 and rng.random() < 0.35:
                    child = indent + rng.choice([2, 2, 4, 1])
                    lines.append(pad + key + sep + "\n" + self.block(child, depth + 1))
                else:
                    value = self.flow(depth) if rng.random() < 0.25 else self.scalar(False, indent)
                    gap = rng.choice([" ", " ", "  ", "\t"])
                    tail = rng.choice(["", "", " # c", "\t# c", "#c", "\t"])
                    lines.append(pad + key + sep + gap + value + tail + "\n")
        else:
            for _ in range(rng.randrange(1, 4)):
                dash = rng.choice(["- ", "- ", "-\t", "-  "])
                value = self.flow(depth) if rng.random() < 0.25 else self.scalar(False, indent)
                lines.append(pad + dash + value + rng.choice(["", " # c", "\t"]) + "\n")
        return "".join(lines)

    def document(self) -> str:
        rng = self.rng
        body = self.flow(0) if rng.random() < 0.2 else self.block(0, 0)
        prefix = rng.choice(
            ["", "", "", "---\n", "--- ", "---\t", "# c\n", "\ufeff", "%YAML 1.1\n---\n"]
        )
        suffix = rng.choice(["", "", "...\n", "\n\n", "\t\n", "# end", "\n\ufeffz: 1\n"])
        text = prefix + body + suffix
        if rng.random() < 0.15:
            text = text.replace("\n", rng.choice(["\r\n", "\r", "\x85", "\u2028"]))
        return text


def _generated_documents(seed: int, count: int) -> list[str]:
    generator = _Generator(random.Random(seed))
    return [generator.document() for _ in range(count)]


@requires_c
def test_generated_documents_read_as_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    _assert_reads_as_pure(_generated_documents(20261024, 2000), monkeypatch)


MUTATION_CHARACTERS = [
    "\t", " ", "\n", ":", "#", "-", '"', "'", "\ufeff", "\x85", "\u2028", "%", "?", ",",
    "[", "]", "{", "}", "\\", "\r", "|", ">",
]  # fmt: skip


def _mutations(texts: list[str], seed: int, per_text: int) -> list[str]:
    """Each text with one or two characters inserted, deleted or replaced."""
    rng = random.Random(seed)
    mutated = []
    for text in texts:
        for _ in range(per_text):
            out = text
            for _ in range(rng.randrange(1, 3)):
                index = rng.randrange(len(out) + 1)
                roll = rng.random()
                if roll < 0.6:
                    out = out[:index] + rng.choice(MUTATION_CHARACTERS) + out[index:]
                elif roll < 0.8:
                    out = out[:index] + out[index + 1 :]
                else:
                    out = out[:index] + rng.choice(MUTATION_CHARACTERS) + out[index + 1 :]
            mutated.append(out)
    return mutated


@requires_c
def test_mutated_documents_read_as_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    small = [text for text in _repo_texts() if len(text) < 4000]
    edge = [text for text in EDGE_CASES.values() if len(text) < 4000]
    seeds = edge + small + _generated_documents(7, 300)
    _assert_reads_as_pure(_mutations(seeds, 11, 3), monkeypatch)


SAMPLED_CODE_POINTS = [
    *range(0x100),
    *range(0x2000, 0x2030),
    *range(0xD7F8, 0xD808),
    *range(0xDFF8, 0xE008),
    *range(0xFDD0, 0xFDF0),
    *range(0xFEF8, 0x10000),
    0x10000,
    0x1F600,
    0x10FFFF,
]
CODE_POINT_TEMPLATES = ["a: x{c}y\n", 'a: "x{c}y"\n', "a: |\n  x{c}y\n", "x{c}y: 1\n", "[x{c}y]"]


@requires_c
def test_sampled_code_points_read_as_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    texts = [
        template.format(c=chr(code))
        for code in SAMPLED_CODE_POINTS
        for template in CODE_POINT_TEMPLATES
    ]
    _assert_reads_as_pure(texts, monkeypatch)


# --- The guard runs in linear time --------------------------------------------------------

ADVERSARIAL_GUARD_INPUTS = {
    "hash_banner": "#" * 5000 + "\na: 1\n",
    "comment_with_many_hashes": "# see " + ", ".join(f"#{i}" for i in range(2000)) + "\na: 1\n",
    "many_comment_lines": "## x\n" * 2000 + "a: 1\n",
    "spaced_hashes": "# " * 2500 + "\na: 1\n",
    "long_line_of_block_header_comments": "a: '" + "| #" * 20000 + "' \nb: 1\n",
    "long_line_of_block_headers_before_space_line": "a: '" + "| #" * 20000 + "'\n \nb: 1\n",
    "many_space_only_lines": "a: |\n \n" + "  x\n \n" * 5000,
    "indented_blank_lines_in_a_block_scalar": "a: |\n" + "  x\n  \n" * 50_000,
    "space_only_lines_after_an_emoji": "t: \U0001f600\n" + "a: 1\n \n" * 100_000,
    "space_only_lines_with_cr_endings": "a: 1\r" + " \r" * 50_000,
}
"""Texts on which the first guard regexes backtracked exponentially or quadratically.

A 24-character ``#`` banner cost 1.4 s and doubled with every ``#``; 8,000 ``| #`` on one
line cost 1.4 s and quadrupled with every doubling; and the first rewrite of the
space-line check scanned back to the start of the text for every line of only spaces,
so 100,000 of them after one emoji (a UCS-4 string) cost 3.6 s. Each of these now takes
a few milliseconds.
"""

_GUARD_ROUTING_PROGRAM = """
import json, sys
from softschema._portable import _needs_pure_parser
json.dump({name: _needs_pure_parser(text) for name, text in json.load(sys.stdin).items()}, sys.stdout)
"""


def test_the_guard_classifies_every_adversarial_input() -> None:
    """Every adversarial text is routed as expected, in a process that can time out.

    A separate process, because the regexes this pins hung for years on these inputs: a
    regression must fail the test, not stall the suite. The only clock is the subprocess
    timeout, and it is a hang guard, not a measurement: the ten texts take well under a
    second together and the patterns they were written against take hours, so no runner
    contention moves a run across it (``ci-and-gates-rules``). The cost itself is gated
    by the deterministic scan count below and, in the ``slow`` tier, by the growth ratio.
    """
    result = subprocess.run(
        [sys.executable, "-c", _GUARD_ROUTING_PROGRAM],
        input=json.dumps(ADVERSARIAL_GUARD_INPUTS),
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "hash_banner": False,
        "comment_with_many_hashes": False,
        "many_comment_lines": False,
        "spaced_hashes": False,
        "long_line_of_block_header_comments": False,
        "long_line_of_block_headers_before_space_line": True,
        "many_space_only_lines": True,
        "indented_blank_lines_in_a_block_scalar": False,
        "space_only_lines_after_an_emoji": False,
        "space_only_lines_with_cr_endings": False,
    }


SPACE_LINE_SHAPES: dict[str, Callable[[int], str]] = {
    "space_only_lines": lambda n: "a: 1\n" + " \n" * n,
    "indented_blank_lines_in_a_block_scalar": lambda n: "a: |\n" + "  x\n  \n" * n,
    "space_only_lines_with_cr_endings": lambda n: "a: 1\r" + " \r" * n,
    "space_only_lines_with_crlf_endings": lambda n: "a: 1\r\n" + " \r\n" * n,
    "space_only_lines_after_an_emoji": lambda n: "t: \U0001f600\n" + "a: 1\n \n" * n,
    "block_header_before_the_last_space_line": lambda n: "a: 1\n" + " \n" * n + "b: |\n \n",
}
"""Texts with ``n`` lines of only spaces, where the space-line loop does its work."""


class _CountingText(str):
    """A ``str`` that records how many characters its ``rfind`` calls may scan."""

    __slots__ = ("calls", "scanned")

    def __new__(cls, text: str) -> _CountingText:
        self = super().__new__(cls, text)
        self.calls = 0
        self.scanned = 0
        return self

    def rfind(self, sub: str, start: int = 0, end: int | None = None, /) -> int:  # pyright: ignore[reportIncompatibleMethodOverride, reportImplicitOverride]
        self.calls += 1
        self.scanned += (len(self) if end is None else end) - start
        return super().rfind(sub, start, end)


class _CountingSearch:
    """Stands in for ``_BLOCK_HEADER_AT_LINE_END`` and records the span of each search."""

    def __init__(self, pattern: re.Pattern[str]) -> None:
        self.pattern = pattern
        self.scanned = 0

    def search(self, text: str, pos: int, endpos: int) -> re.Match[str] | None:
        self.scanned += endpos - pos
        return self.pattern.search(text, pos, endpos)


@pytest.mark.parametrize("n", [1, 2_000, 20_000])
@pytest.mark.parametrize("shape", SPACE_LINE_SHAPES.values(), ids=SPACE_LINE_SHAPES.keys())
def test_the_space_line_guard_looks_back_only_as_far_as_the_previous_line(
    shape: Callable[[int], str], n: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The loop hands ``rfind`` at most twice the text, and the header search at most once.

    A deterministic proxy for the loop's cost, counted rather than timed, so it cannot
    flake on a shared runner (``ci-and-gates-rules``). Each space-only line costs two
    ``rfind`` calls bounded by the previous match and one search over the line before
    it; the spans telescope, so the totals are at most twice and once the text, whatever
    ``n`` is. The first rewrite, which searched from offset 0, hands ``rfind`` about ``n``
    times the text (2,001x at n = 2,000 and 20,001x at n = 20,000 on these shapes), and
    bounding by the previous match's end instead hands the search 1,000x to 10,000x the
    text on consecutive space-only lines; both fail here by three orders of magnitude.
    """
    plain = shape(n)
    expected = _portable._block_scalar_before_space_line(plain)
    text = _CountingText(plain)
    search = _CountingSearch(_portable._BLOCK_HEADER_AT_LINE_END)
    monkeypatch.setattr(_portable, "_BLOCK_HEADER_AT_LINE_END", search)

    assert _portable._block_scalar_before_space_line(text) is expected

    space_only_lines = sum(1 for _ in _portable._SPACE_ONLY_LINE.finditer(plain))
    assert space_only_lines >= n
    # Two lookups per space-only line visited; a hit ends the loop at that line.
    if expected:
        assert text.calls <= 2 * space_only_lines
    else:
        assert text.calls == 2 * space_only_lines
    assert text.scanned <= 2 * len(text), (text.calls, text.scanned, len(text))
    assert search.scanned <= len(text), (search.scanned, len(text))


GROWTH_SHAPES: dict[str, Callable[[int], str]] = {
    "hash_banner": lambda n: "#" * n + "\na: 1\n",
    "comment_lines": lambda n: "## x\n" * n + "a: 1\n",
    "block_header_comments": lambda n: "a: '" + "| #" * n + "' \nb: 1\n",
    "space_only_lines": lambda n: "a: 1\n" + " \n" * n,
    "indented_blank_lines_in_a_block_scalar": lambda n: "a: |\n" + "  x\n  \n" * n,
    "space_only_lines_with_cr_endings": lambda n: "a: 1\r" + " \r" * n,
    "space_only_lines_after_an_emoji": lambda n: "t: \U0001f600\n" + "a: 1\n \n" * n,
}
"""Shapes with a cost that is linear in ``n``; a quadratic term shows between the sizes below."""


@pytest.mark.slow
@pytest.mark.parametrize("shape", GROWTH_SHAPES.values(), ids=GROWTH_SHAPES.keys())
def test_the_guard_cost_grows_linearly_with_the_input(shape: Callable[[int], str]) -> None:
    """A hundred times the input costs under a thousand times the time; a quadratic costs ten thousand.

    This is the one timed check, and it covers the regex patterns, whose work the count
    above cannot see. It is in the ``slow`` tier because a wall-clock ratio on a shared
    runner carries noise (``ci-and-gates-rules``), and it is built so that noise does not
    decide it: the sizes are a hundred apart, so a linear cost (about 100x; the guard
    measures 60x to 200x) and a quadratic one (about 10,000x) sit an order of magnitude
    on either side of the bound; each timing is the best of five after a warm-up; and
    there is no absolute threshold, only the within-run ratio.
    """
    small = _time_guard(shape(2_000))
    large = _time_guard(shape(200_000))
    # The small run is tens of microseconds on some shapes; floor it at timer-noise scale.
    assert large < 1000 * max(small, 0.0001), (small, large)


def _time_guard(text: str, repeats: int = 5) -> float:
    """The best of ``repeats`` timings of the guard on ``text``, after one warm-up run."""
    _portable._needs_pure_parser(text)
    best = math.inf
    for _ in range(repeats):
        start = time.perf_counter()
        _portable._needs_pure_parser(text)
        best = min(best, time.perf_counter() - start)
    return best


# --- Which parser runs ---------------------------------------------------------------------


def _record_parsers(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    """Record, for each ruamel ``YAML`` softschema builds, whether it asked for pure."""
    calls: list[bool] = []
    real = YAML

    def recording(*args: Any, **kwargs: Any) -> Any:
        calls.append(bool(kwargs.get("pure", False)))
        return real(*args, **kwargs)

    monkeypatch.setattr(_portable, "YAML", recording)
    return calls


ROUTED_TO_PURE = {
    "yaml_directive": "%YAML 1.1\n---\na: yes\n",
    "tag_directive": "%TAG !e! tag:example.com,2000:\n---\na: 1\n",
    "directive_on_later_line": "# c\n%YAML 1.2\n---\na: 1\n",
    "directive_after_cr": "# c\r%YAML 1.2\r---\ra: 1\r",
    "tab": "a: 1\t\n",
    "tab_in_quoted": 'a: "x\ty"\n',
    "bom": "a: 1\n\ufeffb: 2\n",
    "nel": "a: x\x85y\n",
    "line_separator": "a: x\u2028y\n",
    "paragraph_separator": "a: x\u2029y\n",
    "block_header_comment": "a: |#c\n  x\n",
    "block_header_space_line": "a: |\n \n  x\n",
    "block_header_space_line_after_comment": "a: >- # c\r\n \r\n  x\r\n",
    "root_block_scalar": "|\n  x\n",
    "root_block_scalar_after_marker_and_comment": "# c\n--- # d\n>\n  x\n",
    "flow_quoted_key_adjacent_colon": '["a":1]',
    "flow_quoted_key_spaced_colon": "['k'  :v]",
    "quoted_key_colon_at_end": '"a":',
    "explicit_key_colon_next_line": '[? "a"\n:x]',
    "explicit_plain_key_colon_after_comment": "[? a #c\n:x]",
    "spaced_colon_in_block_value": "a: x :y\n",
    "repeated_document_end": "a: 1\n...\n...\n",
    "single_document_end": "a: 1\n...\n",
}


@requires_c
@pytest.mark.parametrize("text", ROUTED_TO_PURE.values(), ids=ROUTED_TO_PURE.keys())
def test_disagreement_shapes_skip_the_c_parser(text: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PURE_ENV, raising=False)
    calls = _record_parsers(monkeypatch)
    _outcome(text)
    assert calls == [True]


C_FIRST = {
    "block_mapping": "a: 1\nb:\n  - x\n  - 'y'\nc: {d: [1, 2]}\n",
    "block_scalar": "a: |\n  line\n\n  more\nb: >-\n  folded\n",
    "frontmatter_style": "softschema:\n  contract: example:Doc/v1\ntitle: Spirited Away\n",
    "non_ascii": "title: na\u00efve \U0001f600\n",
    "flow_json_like_mapping": '{"a": 1, "b": [true, null]}  # trailing comment\n',
    "nested_block_scalar_comment_line": "a: |\n  x\n# c\nb: 1\n",
    "ellipsis_and_times": "a: and so on...\nt: 12:30\nu: http://example.com/x\n",
    "banner_comment": "#" * 40 + "\n# Movie page record\n" + "#" * 40 + "\ntitle: x\n",
    "comment_with_block_indicator": "# see | and > below\na: |\n  x\n",
}


@requires_c
@pytest.mark.parametrize("text", C_FIRST.values(), ids=C_FIRST.keys())
def test_ordinary_documents_are_read_by_the_c_parser_alone(
    text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(PURE_ENV, raising=False)
    calls = _record_parsers(monkeypatch)
    expected = _in_reference_process([text])[0]
    assert _same(_outcome(text), expected)
    assert calls == [False]


C_REJECTS = {
    "yaml_error_on_flow_colon": "sources: [https://example.com/a]\n",
    "yaml_error_on_flow_times": "t: [10:30, 11:00]\n",
    "error_code_on_escaped_surrogate": 'a: "\\ud800"\n',
    "error_message_on_duplicate_key": "a: 1\na: 2\n",
    "error_message_on_bad_indent": "a:\n  b: 1\n c: 2\n",
    "encoding_error_on_raw_surrogate": "a: \ud800\n",
    "preflight_error_on_alias": "a: &x 1\nb: *x\n",
    "value_check_error": "a: 9007199254740992\n",
}


@requires_c
@pytest.mark.parametrize("text", C_REJECTS.values(), ids=C_REJECTS.keys())
def test_a_c_parser_failure_is_reread_by_pure(text: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PURE_ENV, raising=False)
    calls = _record_parsers(monkeypatch)
    expected = _in_reference_process([text])[0]
    assert _same(_outcome(text), expected), (_outcome(text), expected)
    assert calls == [False, True]


C_EXCEPTIONS = [
    YAMLError("libyaml refused it"),
    PortableInputError("yaml_limit", "from the C preflight"),
    RecursionError("deep"),
    ValueError("bad value"),
    UnicodeEncodeError("utf-8", "\ud800", 0, 1, "surrogates not allowed"),
    MemoryError(),
    TypeError("unexpected"),
]


@requires_c
@pytest.mark.parametrize("error", C_EXCEPTIONS, ids=lambda error: type(error).__name__)
def test_any_exception_from_the_c_attempt_falls_back_to_pure(
    error: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(PURE_ENV, raising=False)
    real = _portable._parse_with

    def failing_c(text: str, *, pure: bool) -> Any:
        if not pure:
            raise error
        return real(text, pure=pure)

    monkeypatch.setattr(_portable, "_parse_with", failing_c)
    assert parse_yaml("a: [1, x]\n") == {"a": [1, "x"]}
    with pytest.raises(PortableInputError) as raised:
        parse_yaml("a: 1\na: 2\n")
    assert raised.value.code == "yaml_duplicate_key"
    assert "line 1, column 1:\n    a: 1\n    ^ (line: 1)" in str(raised.value)


def test_the_portable_error_from_pure_is_the_one_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without C, or with it forced off, the one parse is pure and errors pass through."""
    monkeypatch.setenv(PURE_ENV, "1")
    calls = _record_parsers(monkeypatch)
    with pytest.raises(PortableInputError) as raised:
        parse_yaml("a: [1\n")
    assert raised.value.code == "yaml_parse_error"
    assert calls == [True]


# --- The switch and the report --------------------------------------------------------------


@requires_c
@pytest.mark.parametrize(
    ("setting", "mode"),
    [(None, "c-first"), ("", "c-first"), ("0", "c-first"), ("1", "pure"), ("yes", "pure")],
)
def test_pure_yaml_switch(setting: str | None, mode: str, monkeypatch: pytest.MonkeyPatch) -> None:
    if setting is None:
        monkeypatch.delenv(PURE_ENV, raising=False)
    else:
        monkeypatch.setenv(PURE_ENV, setting)
    calls = _record_parsers(monkeypatch)
    assert softschema.yaml_parser_mode() == mode
    assert parse_yaml("a: 1\n") == {"a": 1}
    assert calls == ([False] if mode == "c-first" else [True])


def test_mode_is_pure_without_the_c_extension() -> None:
    assert _in_reference_process("mode") == "pure"


def test_mode_is_pure_when_the_c_extension_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PURE_ENV, raising=False)
    monkeypatch.setattr(_portable, "_C_PARSER_AVAILABLE", False)
    calls = _record_parsers(monkeypatch)
    assert softschema.yaml_parser_mode() == "pure"
    assert parse_yaml("a: 1\n") == {"a": 1}
    assert calls == [True]


@requires_c
def test_mode_reports_the_c_parser_when_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PURE_ENV, raising=False)
    assert softschema.yaml_parser_mode() == "c-first"


@requires_c
def test_the_installed_c_parser_is_the_checked_libyaml_build() -> None:
    """The dev group's clib bundles the libyaml the guards were derived for, so C-first runs."""
    module = sys.modules[YAML(typ="safe").Parser.__module__]
    assert _portable._libyaml_version(module) == _portable.CHECKED_LIBYAML_VERSION
    assert _portable._c_parser_is_checked()


@requires_c
def test_another_libyaml_build_keeps_every_text_on_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_portable, "CHECKED_LIBYAML_VERSION", "0.2.5")
    assert not _portable._c_parser_is_checked()


@requires_c
def test_an_unchecked_ruamel_release_keeps_every_text_on_pure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_portable, "CHECKED_RUAMEL_VERSIONS", ((9, 0), (9, 1)))
    assert not _portable._c_parser_is_checked()


def test_no_libyaml_version_without_the_extension() -> None:
    assert _portable._libyaml_version(None) is None
    assert _portable._libyaml_version(object()) is None


@requires_c
def test_the_gate_reads_the_bare_extension_module_when_the_qualified_name_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Older clib releases register only ``_ruamel_yaml``, which ruamel itself imports."""
    qualified = YAML(typ="safe").Parser.__module__
    if qualified != "_ruamel_yaml":
        monkeypatch.setitem(sys.modules, "_ruamel_yaml", sys.modules[qualified])
        monkeypatch.delitem(sys.modules, qualified)
    assert _portable._installed_libyaml_version() == _portable.CHECKED_LIBYAML_VERSION


@requires_c
def test_the_reason_names_why_the_parser_is_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PURE_ENV, raising=False)
    assert _portable.yaml_parser_reason().startswith("ruamel.yaml.clib (libyaml 0.1.7)")
    monkeypatch.setenv(PURE_ENV, "1")
    assert _portable.yaml_parser_reason() == f"turned off by {PURE_ENV}"
    monkeypatch.delenv(PURE_ENV, raising=False)
    monkeypatch.setattr(_portable, "CHECKED_LIBYAML_VERSION", "0.2.5")
    assert _portable.yaml_parser_reason() == "libyaml 0.1.7 is not the checked build 0.2.5"
    monkeypatch.setattr(_portable, "CHECKED_LIBYAML_VERSION", "0.1.7")
    monkeypatch.setattr(_portable, "CHECKED_RUAMEL_VERSIONS", ((9, 0), (9, 1)))
    assert _portable.yaml_parser_reason().endswith("is outside the checked releases 9.0 to 9.0")


def test_the_reason_without_the_extension_is_that_it_is_not_installed() -> None:
    assert _in_reference_process("reason") == "ruamel.yaml.clib is not installed"


# --- The differential search harness runs ---------------------------------------------------


@requires_c
def test_the_fuzz_harness_runs_and_finds_no_divergence(capsys: pytest.CaptureFixture[str]) -> None:
    """``devtools/yaml_parser_fuzz.py`` keeps working when ``_parse_with`` or the guard changes."""
    import importlib.util

    path = REPO_ROOT / "devtools" / "yaml_parser_fuzz.py"
    spec = importlib.util.spec_from_file_location("yaml_parser_fuzz", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.main(["1500", "--batch", "1000", "--jobs", "1"]) == 0
    out = capsys.readouterr().out
    assert "texts: 1500 " in out
    assert "divergences: 0" in out
    assert "libyaml 0.1.7" in out


# --- The compiled-schema writer does not depend on the extension ----------------------------


COMPILE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Emoji \U0001f600 and an astral \U00010000",
    "description": " ".join(["word"] * 1200),
    "properties": {"name": {"type": "string", "description": "x" * 5000}},
    "type": "object",
}


@requires_c
def test_compiled_schema_bytes_do_not_depend_on_the_c_emitter(tmp_path: Path) -> None:
    """The C emitter escapes astral characters and wraps long lines differently."""
    from frontmatter_format import new_yaml

    from softschema.compile import _yaml_dump

    module = tmp_path / "tests_c_parser_schema.py"
    module.write_text(f"SCHEMA = {COMPILE_SCHEMA!r}\n", encoding="utf-8")
    reference = _in_reference_process("compile", extra_path=tmp_path)
    assert "\U0001f600" in reference
    assert _yaml_dump(COMPILE_SCHEMA) == reference

    # The fixture discriminates: through libyaml's emitter the same dump differs.
    unpinned = new_yaml(key_sort=str, suppress_vals=None, typ="safe")
    unpinned.width = 4096
    buffer = io.StringIO()
    unpinned.dump(COMPILE_SCHEMA, buffer)
    assert unpinned.Emitter.__name__ == "CEmitter"
    assert buffer.getvalue() != reference
