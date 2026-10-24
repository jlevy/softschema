"""Bounded UTF-8 and portable YAML input shared by artifact and schema reads."""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any, Literal

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
from ruamel.yaml.parser import Parser as RuamelParser

MAX_SAFE_INTEGER = 9_007_199_254_740_991
"""Largest integer that survives a round trip through a JS number."""

MAX_DEPTH = 64
"""Simultaneously open collections, including the root.

A portability rule, not a resource guard, which is why it survives while the input,
node, and scalar ceilings did not. Those three only answered whether a hostile document
could exhaust the parser, and softschema reads artifacts its own callers just wrote.
Depth answers a different question: how deep a document still means the same thing in
both runtimes.

Without an explicit rule the host stack decides, and the two hosts disagree by an order
of magnitude. CPython's default recursion limit of 1,000 lets this constructor reach
depth 491 from an empty caller stack — less from a real one, since the caller's own
frames come out of the same budget — while V8 parses past 10,000. A document between
those two bounds would be valid in TypeScript and a crash in Python, which is exactly
what the shared vectors exist to prevent.

64 is far above any real artifact and leaves roughly 7x headroom under the measured
ceiling, so the check below always fires before the recursion does. Raising it is safe
only while that headroom holds; past a few hundred the Python guard stops being reachable
and `RecursionError` takes over.
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


BOM = "\ufeff"
"""A leading byte order mark, which decoding removes rather than keeps as a character."""


def read_utf8(path: Path) -> str:
    """Read one UTF-8 artifact, dropping a leading byte order mark.

    The BOM has to go, and it has to go here, because this is the one function both
    runtimes route every artifact and schema read through. TypeScript decodes with
    ``TextDecoder("utf-8")``, whose default ``ignoreBOM: false`` means "strip it"; Python's
    ``bytes.decode`` keeps it as a U+FEFF character. Left alone, that one invisible byte
    made the two implementations reach opposite verdicts on identical files: the fence
    scan and the reader both compare a first line against ``---``, and ``"\ufeff---"`` is
    not ``"---"``, so Python called a BOM-prefixed artifact fenceless while TypeScript read
    it without complaint.

    Reporting that document as having no frontmatter is the diagnostic this codebase
    exists to avoid — the block is plainly there, and an agent sent looking for it finds
    nothing to fix. Stripping is also what the encoding standard asks for: the mark
    announces the encoding, it is not content. Only position zero is examined; a U+FEFF
    anywhere else is a real character and survives.
    """
    try:
        text = path.read_bytes().decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PortableInputError("invalid_utf8", "input is not valid UTF-8") from exc
    return text[1:] if text.startswith(BOM) else text


def parse_yaml(text: str) -> Any:
    """Parse one portable YAML document as pure-Python ruamel reads it.

    Pure ruamel's reading is the contract: the value, its types, its key order, and any
    error code and message. Two faster readers stand in for it only where they are known
    to give exactly that result. :func:`_parse_json_subset` hands a strict JSON document
    to :mod:`json` when pure ruamel reads that text to an identical value, and
    :func:`_parse_with_ruamel` uses ruamel's optional C extension, when installed, on
    texts where libyaml and pure ruamel agree, re-reading with pure ruamel whenever the
    C parser fails. Every path ends in the same :func:`_check_value`.
    """
    value = _parse_json_subset(text)
    if value is _NOT_JSON:
        return _parse_with_ruamel(text)
    _check_value(value)
    return value


PURE_YAML_ENV = "SOFTSCHEMA_PURE_YAML"
"""Environment variable that, set to anything but empty or ``0``, turns off the C parser.

For diagnosis: results are the same either way, so this only changes speed and which
parser :func:`yaml_parser_mode` reports. It is read on every parse.
"""

_C_PARSER_AVAILABLE = YAML(typ="safe").Parser is not RuamelParser
"""Whether ruamel found its optional C extension (``ruamel.yaml.clib``) at import."""


def yaml_parser_mode() -> Literal["c-first", "pure"]:
    """Which ruamel parser :func:`parse_yaml` reads YAML with in this process.

    ``"c-first"`` means ruamel's C extension is installed and not turned off with
    ``SOFTSCHEMA_PURE_YAML``: texts are read by libyaml where it is known to agree with
    pure ruamel, and by pure ruamel otherwise. ``"pure"`` means every text is read by
    pure ruamel, because the extension is absent or turned off. Results are identical in
    both modes; only speed differs.
    """
    return "c-first" if _c_parser_active() else "pure"


def _c_parser_active() -> bool:
    return _C_PARSER_AVAILABLE and os.environ.get(PURE_YAML_ENV, "") in ("", "0")


_C_FAILED: Any = object()
"""What :func:`_try_c_parser` returns when the C parser could not read a text."""

_PURE_ONLY_CHARACTERS = ("\x85", "\u2028", "\u2029", "\ufeff")
"""NEL, LS, PS and a byte order mark, which libyaml and pure ruamel handle differently.

Both treat the first three as line breaks, but not in the same places: ``-\\x85-`` is one
nested sequence to pure ruamel and two entries to libyaml, and a NEL inside a plain
scalar folds to a space in pure ruamel and is an error in libyaml. libyaml also skips a
byte order mark at the start of any line, where pure ruamel skips one only at the start
of the text and otherwise keeps it as content.
"""

_BLOCK_HEADER_COMMENT = re.compile(r"#(?:(?<=[|>]#)|(?<=[|>][-+0-9]#)|(?<=[|>][-+0-9]{2}#))")
"""A block scalar header with a comment and no space before it, such as ``|#``.

Pure ruamel rejects it; libyaml reads the comment. A header has at most two indicator
characters; libyaml rejects a longer one too. The pattern starts at the ``#`` so the
search skips ahead to each one.
"""

_BLOCK_SPACE_LINE = re.compile(r"[|>][-+0-9]*(?: +#[^\r\n]*| *)(?:\r\n?|\n) +(?:\r\n?|\n)")
"""A block scalar header followed by a line of only spaces.

When such a line has fewer spaces than a later leading line, pure ruamel reports "more
indented follow up line than first in a block scalar"; libyaml reads the scalar.
"""

_ROOT_BLOCK_SCALAR = re.compile(r"(?:[ \r\n]|#[^\r\n]*|(?:---|\.\.\.)(?=[ \r\n]|\Z))*[|>]")
"""A document that is a block scalar, after any blank lines, comments and markers.

Its content may start at column zero, where libyaml reads a ``#`` line as a comment and
pure ruamel as content.
"""

_SPACED_COLON = re.compile(r":(?<=[ \"']:)(?![ \r\n])")
"""A colon after a space or quote and before anything but a space or line break.

Every :data:`_FLOW_KEY_COLON` match ends in one, and starting at the colon lets the search
skip ahead to each colon instead of testing every character.
"""

_FLOW_KEY_COLON = re.compile(r"[\"'] *:(?![ \r\n])")
"""A quoted scalar followed by a colon that is not followed by a space or line break.

In a flow sequence such as ``["a":1]``, libyaml reads the colon as a mapping indicator
and pure ruamel, following YAML 1.2, does not, and rejects the text.
"""


def _needs_pure_parser(text: str) -> bool:
    """Whether ``text`` has a shape on which libyaml may read what pure ruamel rejects.

    Texts libyaml rejects need no guard here, because a C failure is always re-read by
    pure ruamel. These guards cover the other direction, which a fallback cannot catch:
    libyaml accepting a text pure ruamel rejects, or reading it to a different value.
    Each was found by comparing the two parsers over generated and mutated documents,
    and each is pinned by a test in ``test_c_parser.py``. A tab anywhere is the largest:
    libyaml skips a tab between block tokens, after a value or a colon, where pure ruamel
    refuses it, and telling those tabs from harmless ones would take a scanner.

    A line starting with ``%`` is where a directive can be, and libyaml ignores
    ``%YAML 1.1`` when values are resolved, so ``yes`` would stay a string and ``017``
    an integer seventeen.

    Each check is a substring test or a search that skips ahead to a literal character,
    so the whole guard costs a few percent of a C parse.
    """
    if "\t" in text:
        return True
    if not text.isascii() and any(char in text for char in _PURE_ONLY_CHARACTERS):
        return True
    if "%" in text and (text.startswith("%") or "\n%" in text or "\r%" in text):
        return True
    if _BLOCK_HEADER_COMMENT.search(text) is not None:
        return True
    if (" \n" in text or " \r" in text) and _BLOCK_SPACE_LINE.search(text) is not None:
        return True
    if _SPACED_COLON.search(text) is not None and _FLOW_KEY_COLON.search(text) is not None:
        return True
    return _ROOT_BLOCK_SCALAR.match(text) is not None


def _parse_with_ruamel(text: str) -> Any:
    """Parse YAML as pure ruamel does, through ruamel's C parser where that is exact.

    With the C extension active, a text without any shape from :func:`_needs_pure_parser`
    is read by libyaml first. Any exception from that attempt, from the scanner, the
    preflight, construction or :func:`_check_value`, discards it, and pure ruamel reads
    the same text again, so whatever pure ruamel returns or raises is the result. Only a
    text libyaml reads to a value without error keeps libyaml's result, and on those the
    two parsers agree.
    """
    if _c_parser_active() and not _needs_pure_parser(text):
        value = _try_c_parser(text)
        if value is not _C_FAILED:
            return value
    return _parse_with(text, pure=True)


def _try_c_parser(text: str) -> Any:
    """The C parser's reading of ``text``, or :data:`_C_FAILED` if it raised anything."""
    try:
        return _parse_with(text, pure=False)
    except Exception:
        return _C_FAILED


def _parse_with(text: str, *, pure: bool) -> Any:
    """Parse YAML after a representation preflight, both through the same parser.

    ``pure=False`` selects ruamel's C parser when it is installed. The preflight's event
    pass and the load use one ``YAML`` handle, so they always run on the same parser.
    """
    yaml = YAML(typ="safe", pure=pure)
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
                if len(stack) > MAX_DEPTH:
                    raise PortableInputError("yaml_limit", "YAML nesting exceeds the depth limit")
            elif isinstance(event, (MappingEndEvent, SequenceEndEvent)):
                stack.pop()
        if has_alias:
            raise PortableInputError("yaml_alias", "YAML aliases and anchors are not supported")
        value = yaml.load(text)
    except PortableInputError:
        raise
    except RecursionError as exc:
        # The preflight above rejects anything past MAX_DEPTH, so construction should
        # never recurse this far. Mirror the TypeScript RangeError handler anyway: a
        # caller already deep in its own stack can exhaust the budget at a legal depth,
        # and that has to stay a structured result rather than escape validate_artifact.
        raise PortableInputError("yaml_limit", "YAML nesting exhausted the parser stack") from exc
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


_NOT_JSON: Any = object()
"""What :func:`_parse_json_subset` returns for a text it leaves to ruamel."""

_JSON_ROOT = re.compile(r"[ \n\r]*[\[{]")
"""A root JSON array or object, preceded by whitespace that ruamel also skips.

ruamel skips a tab only inside a flow collection, so a tab before the root is a YAML
error although JSON calls it whitespace; :func:`_parse_json_subset` checks the text
after the root the same way. Space and line breaks are whitespace to both. A scalar
root is left to ruamel: it is cheap there and rare.
"""

_JSON_WHITESPACE = " \t\n\r"

_JSON_UNSAFE_CHARACTER = re.compile(r"[\x7f-\x9f\u2028\u2029\ud800-\udfff\ufffe\uffff]")
"""Raw characters JSON accepts in a string and ruamel does not read the same way.

ruamel's reader rejects DEL, the C1 controls, a raw surrogate, U+FFFE and U+FFFF
outright, and its scanner treats NEL, U+2028 and U+2029 as line breaks, which folds a
quoted string and moves where a key ends. The C0 controls other than tab, line feed and
carriage return are absent already, because strict ``json`` refuses them raw. The
escaped form of any of these but a surrogate, such as ``\\u2028``, decodes identically
in both.
"""

_JSON_SURROGATE_ESCAPE = re.compile(r"\\u[dD][89a-fA-F]")
"""An escaped UTF-16 surrogate, which ruamel decodes one half at a time.

``json`` joins an escaped pair into one character; ruamel produces two lone surrogates,
which :func:`_check_value` rejects. Any text with such an escape goes to ruamel. The
pattern also matches an escaped backslash followed by ``ud8..``, which only costs that
text the fast path.
"""

_JSON_KEY_LIMIT = 128
"""Longest key, in decoded characters, that the JSON path accepts.

YAML limits an implicit key to 1024 characters, measured in the source from the key's
opening quote to its colon, and ruamel enforces that inside flow mappings too: a longer
key is a parse error there. A decoded character is at most six source characters
(``\\uXXXX``; escaped surrogates never reach this path), so 128 decoded characters keep
the key itself within 770 source characters, quotes included.
"""

_JSON_GAP_LIMIT = 200
"""Fewest spaces or tabs between a key and its colon that send a text to ruamel.

With a key of at most 770 source characters and fewer than 200 characters of gap, the
key's extent stays under ruamel's 1024.
"""

_JSON_SPACED_COLON = re.compile(r":(?<=[ \t\r\n]:)")
"""A colon right after whitespace, which both key patterns below need.

Most JSON writes ``"key": value`` and has none, so this one cheap scan (it starts from
the literal colon) usually rules both out.
"""

_JSON_KEY_LINE_BREAK = re.compile(r"[\r\n][ \t]*:")
"""A colon on a later line than its key, which YAML does not allow for a flow key.

In strict JSON a raw line break can only sit between tokens, and the only token a colon
follows is a key, so this matches exactly the keys separated from their colon by one:
the last break before such a colon is followed only by spaces and tabs.
"""

_JSON_KEY_GAP = re.compile(rf"(?<![ \t])[ \t]{{{_JSON_GAP_LIMIT},}}:")


class _NotPortableJson(Exception):
    """Raised inside a ``json`` hook to hand the whole text to ruamel."""


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build one object, refusing what ruamel reads differently.

    A duplicate key is ``yaml_duplicate_key`` to ruamel and a silent overwrite to
    ``json``, and a ``<<`` key is a merge-key rejection in ruamel's preflight. Both, and an
    over-long key, leave the whole text to ruamel, which reports them as it always has.
    """
    obj = dict(pairs)
    if len(obj) != len(pairs) or "<<" in obj or (obj and max(map(len, obj)) > _JSON_KEY_LIMIT):
        raise _NotPortableJson
    return obj


def _json_constant(_name: str) -> Any:
    """``NaN`` and ``Infinity`` are not JSON; YAML reads them as plain-scalar strings."""
    raise _NotPortableJson


def _json_has_unsafe_character(text: str) -> bool:
    """Whether ``text`` holds a raw character ruamel reads differently from ``json``.

    An ASCII text can only hold DEL, because ``json`` refuses the C0 controls.
    """
    if text.isascii():
        return "\x7f" in text
    return _JSON_UNSAFE_CHARACTER.search(text) is not None


def _json_within_depth(root: Any) -> bool:
    """Whether no more than :data:`MAX_DEPTH` collections are ever open at once."""
    level = [root]
    for _ in range(MAX_DEPTH):
        level = [
            child
            for node in level
            for child in (node.values() if type(node) is dict else node)
            if type(child) is dict or type(child) is list
        ]
        if not level:
            return True
    return False


def _parse_json_subset(text: str) -> Any:
    """The value of a strict JSON text that pure ruamel reads identically, else ``_NOT_JSON``.

    This never raises; a text it declines is simply left to :func:`_parse_with_ruamel`,
    which is how every disagreement between the two languages keeps today's outcome.
    The reference is pure ruamel whether or not the C extension is installed, because
    :func:`_parse_with_ruamel` reads every text as pure ruamel does either way.

    Strict JSON maps onto YAML 1.2 flow syntax token for token: braces, brackets, commas
    and colons are flow indicators, a JSON string is a double-quoted scalar with the same
    escapes, and a JSON number, ``true``, ``false`` or ``null`` is a plain scalar that
    ruamel's YAML 1.2 resolver types as JSON does: an integer without a fraction or
    exponent, a float with either. JSON text cannot spell a tag, anchor, alias, comment,
    directive or block scalar. What remains is the list of places the two still differ,
    each of which sends the text to ruamel:

    - anything ``json`` rejects, including a BOM, empty text, and integers too long for
      ``int``, and a ``RecursionError`` from very deep nesting;
    - ``NaN``, ``Infinity`` and ``-Infinity`` (:func:`_json_constant`);
    - duplicate keys, a ``<<`` key, and long keys (:func:`_json_object`);
    - tabs outside the root collection (:data:`_JSON_ROOT`);
    - raw characters ruamel refuses or treats as line breaks
      (:data:`_JSON_UNSAFE_CHARACTER`) and escaped surrogates
      (:data:`_JSON_SURROGATE_ESCAPE`);
    - a key separated from its colon by a line break or a long gap
      (:data:`_JSON_KEY_LINE_BREAK`, :data:`_JSON_KEY_GAP`);
    - nesting past :data:`MAX_DEPTH`, which ruamel's preflight reports as ``yaml_limit``.

    The tests in ``test_json_fast_path.py`` check each of these against ruamel and
    compare both paths over generated documents built to hit them.
    """
    if _JSON_ROOT.match(text) is None:
        return _NOT_JSON
    try:
        value = json.loads(text, object_pairs_hook=_json_object, parse_constant=_json_constant)
    except (_NotPortableJson, ValueError, RecursionError):
        return _NOT_JSON
    if "\t" in text[len(text.rstrip(_JSON_WHITESPACE)) :]:
        return _NOT_JSON
    if _json_has_unsafe_character(text) or _JSON_SURROGATE_ESCAPE.search(text):
        return _NOT_JSON
    if _JSON_SPACED_COLON.search(text) and (
        _JSON_KEY_LINE_BREAK.search(text) or _JSON_KEY_GAP.search(text)
    ):
        return _NOT_JSON
    if not _json_within_depth(value):
        return _NOT_JSON
    return value


@dataclass(frozen=True)
class FrontmatterSplit:
    """Where a frontmatter-md document's metadata sits inside its text.

    All three fields are character offsets into the *original* text, so a caller can put
    the document back together exactly:

        text[:metadata_offset] + new_metadata + text[metadata_end:body_offset] + body

    That middle slice is the closing fence, kept verbatim rather than re-synthesized.
    This is the difference from :func:`read_frontmatter_doc`, which splits on
    ``splitlines()`` and rejoins with ``"\n"``: fine for reading values, lossy for
    writing the file back.
    """

    metadata_text: str
    metadata_offset: int
    body_offset: int

    @property
    def metadata_end(self) -> int:
        return self.metadata_offset + len(self.metadata_text)


def split_frontmatter(text: str) -> FrontmatterSplit | None:
    """Split a frontmatter-md document without disturbing its body.

    Returns ``None`` when there is no frontmatter *region to rewrite*: no leading fence,
    an unterminated fence, or an empty block whose end fence is the very next line.

    That is narrower than it looks, and the difference matters. Of those three,
    :func:`read_frontmatter_doc` agrees on two — it reports no frontmatter for a
    document with no leading fence and for an empty block — but an unterminated fence is
    a *reader error* there, not a fenceless document. So ``None`` from this function
    must never be read as "this document has no frontmatter fence"; use
    :func:`opens_frontmatter_fence` for that question. Reading ``None`` as fenceless is
    what once let profile detection route an unterminated-fence document to pure-yaml
    and call it valid while the reader refused to open it at all.

    The scan is deliberately hand-rolled and byte-oriented rather than delegated to
    ``frontmatter_format``, for two reasons. The fence rules have to stay identical to
    that reader's — if the two disagree about where the frontmatter ends, a repair pass
    writes one region and validation reads another. And the TypeScript implementation has
    no equivalent package, so writing the same scan twice is what keeps the two runtimes
    splitting identically.
    """
    first = _line_end(text, 0)
    if first is None or text[: first[0]].rstrip() != "---":
        return None
    metadata_offset = first[1]
    cursor = metadata_offset
    while cursor < len(text):
        line = _line_end(text, cursor)
        if line is None:
            break  # unreachable: the loop guard guarantees a line remains
        if text[cursor : line[0]].rstrip() == "---":
            metadata_text = text[metadata_offset:cursor]
            # An empty block (end fence on the very next line) is the portable
            # no_frontmatter case, the same as the reader's ``end == 1``.
            if not metadata_text.strip():
                return None
            return FrontmatterSplit(
                metadata_text=metadata_text,
                metadata_offset=metadata_offset,
                body_offset=line[1],
            )
        cursor = line[1]
    return None  # unterminated fence: no region to rewrite (still a reader error)


def opens_frontmatter_fence(text: str) -> bool:
    """Whether the document's first line is a frontmatter opening fence.

    Profile detection needs this and cannot use :func:`split_frontmatter`, which returns
    ``None`` both for a document that never opened a fence and for one that opened a
    fence and never closed it. Those two get opposite treatment: the first may be a
    pure-yaml artifact, while the second is a frontmatter-md document that the reader
    will reject. Detection has to tell them apart before it can decide a profile, and it
    has to do so without parsing, because an artifact awaiting repair does not parse.

    Only the opening fence is examined; a document that opens one is frontmatter-md
    whether or not it closes it, exactly as :func:`read_frontmatter_doc` treats it.
    """
    first = _line_end(text, 0)
    return first is not None and text[: first[0]].rstrip() == "---"


def _line_end(text: str, start: int) -> tuple[int, int] | None:
    """The content end (before the line break) and the start of the next line.

    A final line with no trailing newline is a line. Its content ends at EOF, and the
    "next line" starts there too, so a caller that keeps scanning stops on the next
    iteration.

    That has to be so, because :func:`read_frontmatter_doc` splits with ``splitlines()``
    and ``readFrontmatterDoc`` with ``split(/\r?\n/)``, and both keep such a line. A scan
    that dropped it would disagree with the reader about where a document's fences are,
    which is the disagreement this module exists to prevent. Concretely, it made
    :func:`split_frontmatter` report "no region to rewrite" for a document ending exactly
    at its closing fence, so ``--repair`` silently skipped an artifact it could fix, and
    it made :func:`opens_frontmatter_fence` call a lone ``---`` fenceless.

    Returns ``None`` only when ``start`` is at or past the end, where no line remains.
    """
    if start >= len(text):
        return None
    index = text.find("\n", start)
    if index == -1:
        return len(text), len(text)
    return index, index + 1


def round_trip_yaml() -> YAML:
    """A ruamel round-trip parser/emitter that preserves how the author wrote things.

    Round-trip mode is what lets a one-scalar correction stay a one-scalar diff: quotes,
    comments, key order, and long lines survive because the loader hands back nodes that
    remember their own notation.

    ``allow_aliases`` is deliberately absent. metaproc's equivalent enables it to keep an
    author's ``*ref`` from expanding into a duplicated mapping, but softschema's
    :func:`parse_yaml` rejects aliases and anchors outright, so an artifact carrying one
    never reaches this emitter.

    The null representer is pinned anyway. ruamel spells a null as an empty value once
    any object has been represented and as ``null`` before that, which makes the spelling
    depend on position in the document. A null this pass did not touch changing shape is
    exactly the unasked-for diff round-trip mode exists to prevent.
    """
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 4096  # never re-wrap an author's long line
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.representer.add_representer(
        type(None),
        lambda dumper, _data: dumper.represent_scalar("tag:yaml.org,2002:null", "null"),
    )
    return yaml


def dump_round_trip(yaml: YAML, document: Any) -> str:
    """Serialize a round-trip document back to text."""
    buffer = StringIO()
    yaml.dump(document, buffer)
    return buffer.getvalue()


def write_artifact_text(path: Path, text: str) -> None:
    """Write an artifact back: atomically, and without touching its line endings.

    The one write path for every pass that rewrites an artifact (repair, conform, the
    combined pipeline), so the "atomic, endings untouched" contract has a single home.
    ``newline=""`` disables Python's newline translation — the text carries exactly the
    endings the caller preserved.
    """
    from strif import atomic_output_file

    with atomic_output_file(path) as tmp:
        Path(tmp).write_text(text, encoding="utf-8", newline="")
