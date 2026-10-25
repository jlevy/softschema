"""Bounded UTF-8 and portable YAML input shared by artifact and schema reads."""

from __future__ import annotations

import json
import math
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any, Literal

import ruamel.yaml
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
from ruamel.yaml.representer import RoundTripRepresenter

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


_SURROGATE = re.compile("[\ud800-\udfff]")


class _PortableConstructor(SafeConstructor):
    """Safe constructor overrides scoped to softschema parser instances."""

    def construct_scalar(self, node: Any) -> Any:  # pyright: ignore[reportImplicitOverride]
        """Join a surrogate pair written as two ``\\u`` escapes into the character it encodes.

        ruamel decodes ``"\\ud83d\\ude00"`` to two lone surrogates, where the ``yaml``
        package, working in UTF-16, reads the one character U+1F600, as JSON does. The
        two engines must agree on that text, and the JSON reading is the one a producer
        that serializes with ``ensure_ascii`` relies on. A surrogate that pairs with
        nothing is left as it is, for :func:`_check_value` to reject as unsupported.
        """
        value = super().construct_scalar(node)
        if isinstance(value, str) and _SURROGATE.search(value):
            try:
                return value.encode("utf-16-le", "surrogatepass").decode("utf-16-le")
            except UnicodeDecodeError:
                return value
        return value


def _construct_value_key_as_string(_constructor: SafeConstructor, node: ScalarNode) -> str:
    """Read a plain ``=`` as the string ``=``, as YAML 1.2 and the ``yaml`` package do.

    ruamel's resolver still tags a plain ``=`` as the YAML 1.1 ``!!value`` key, for which
    the safe constructor has no entry, so the one-character string was a parse error in
    Python and the string ``=`` in TypeScript.
    """
    return node.value


class _NegativeZero(int):
    """An integer literal spelled ``-0``: zero to Python, negative zero to JavaScript.

    A JSON or YAML number is a double in the ``yaml`` package, where ``-0`` keeps its sign,
    and an ``int`` in ruamel, where it cannot. The spec rejects negative zero, so the
    constructor marks the literal and :func:`_check_value` rejects it exactly where it
    rejects ``-0.0``. The marked value never leaves this module.
    """


_NEGATIVE_ZERO_INTEGER = re.compile(r"-0+")
"""The decimal integer literals that are zero with a minus sign (``-0``, ``-00``).

Only the decimal form is negative zero in both engines; the ``yaml`` package reads
``-0x0``, ``-0o0`` and ``-0_0`` as strings.
"""


def _construct_portable_int(constructor: SafeConstructor, node: ScalarNode) -> int:
    """Construct an integer, marking a ``-0`` literal for :func:`_check_value`."""
    value = SafeConstructor.construct_yaml_int(constructor, node)
    if value == 0 and _NEGATIVE_ZERO_INTEGER.fullmatch(node.value) is not None:
        return _NegativeZero(0)
    return value


# The first subclass registration copies ruamel's inherited constructor registry.
_PortableConstructor.add_constructor("tag:yaml.org,2002:timestamp", _construct_timestamp_as_string)
_PortableConstructor.add_constructor("tag:yaml.org,2002:value", _construct_value_key_as_string)
_PortableConstructor.add_constructor("tag:yaml.org,2002:int", _construct_portable_int)


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
        raise PortableInputError(
            "invalid_utf8", f"{document_label(path)}: input is not valid UTF-8"
        ) from exc
    return text[1:] if text.startswith(BOM) else text


_CONTROL_CHARACTER = re.compile("[\x00-\x1f\x7f-\x9f]")


def document_label(path: Path | str) -> str:
    """The backticked document name every message that names a document begins with.

    C0 and C1 control characters and DEL in the name are written as ``#xHHHH``, the
    notation the preflight uses for a rejected character. A path is untrusted input like
    the artifact it names: a filename carrying an escape sequence would otherwise reach
    stderr raw, where a terminal acts on it (an OSC title or clipboard write, a line
    cleared and overwritten, a forged second diagnostic line). JSON output escapes the
    string on its own, so only the human-readable channel needed this. Keep the rule
    identical to ``documentLabel`` in ``portable.ts``.
    """
    name = _CONTROL_CHARACTER.sub(lambda match: f"#x{ord(match.group()):04x}", str(path))
    return f"`{name}`"


_NON_PORTABLE_CHARACTER = re.compile(
    "[^\t\n\r\x20-\x7e\xa0-\u2027\u202a-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]|\r(?!\n)"
)
"""A raw character the two YAML engines read differently.

The class is YAML 1.2 ``c-printable`` with the three Unicode line separators taken out,
plus a carriage return that does not begin a ``\\r\\n`` sequence. ruamel rejects
everything outside ``c-printable`` (its ``Reader.NON_PRINTABLE``) and the ``yaml``
package reads it as content; for U+0085, U+2028 and U+2029 ruamel follows YAML 1.1 and
treats them as line breaks, folding a NEL in a flow scalar to a space and breaking a
block scalar or a comment into a parse error, while the ``yaml`` package again reads them
as content. A lone carriage return is the same shape: a YAML line break for ruamel, so a
CR-only document is many lines and a CR inside a flow scalar folds to a space, while the
``yaml`` package reads it as content and sees one long line. Neither reading can be
reproduced in the other engine, so the portable rule is to accept none of them raw. Every
one of them can be written as a double-quoted escape (``"\\f"``, ``"\\x7f"``, ``"\\N"``,
``"\\L"``, ``"\\P"``, ``"\\r"``), which both engines decode identically. Keep this class
identical to ``NON_PORTABLE_CHARACTER`` in ``portable.ts``.
"""

_NAMED_ESCAPES = {
    0x00: "\\0",
    0x07: "\\a",
    0x08: "\\b",
    0x0B: "\\v",
    0x0C: "\\f",
    0x0D: "\\r",
    0x1B: "\\e",
    0x85: "\\N",
    0x2028: "\\L",
    0x2029: "\\P",
}


def portable_escape(char: str) -> str:
    """The double-quoted YAML escape for one character, as both engines decode it.

    YAML 1.2 names the common controls and the three line separators; everything else
    takes the fixed-width ``\\xHH``, ``\\uHHHH`` or ``\\UHHHHHHHH`` form. Used in the
    preflight message and by ``repair`` when it rewrites a rejected character.
    """
    code = ord(char)
    if code in _NAMED_ESCAPES:
        return _NAMED_ESCAPES[code]
    if code <= 0xFF:
        return f"\\x{code:02x}"
    if code <= 0xFFFF:
        return f"\\u{code:04x}"
    return f"\\U{code:08x}"


def find_non_portable_character(text: str) -> re.Match[str] | None:
    """The first raw character in ``text`` that :func:`check_portable_text` rejects."""
    return _NON_PORTABLE_CHARACTER.search(text)


def check_portable_text(text: str) -> None:
    """Reject the first raw character in ``text`` that the engines would read differently.

    Runs before the engine sees the text, on the whole YAML text the reader was handed:
    the frontmatter block or the entire pure-yaml document, comments and keys included.
    The line and column are counted within that text, as the engines count them; the
    frontmatter reader adds the fence offset so the message names a line of the file.
    Raising here, with one message in both runtimes, is what keeps a mis-decoded cp1252
    ellipsis (which arrives as U+0085) from silently becoming a space in one runtime and
    staying a character in the other.
    """
    match = _NON_PORTABLE_CHARACTER.search(text)
    if match is None:
        return
    index = match.start()
    line = text.count("\n", 0, index) + 1
    column = index - (text.rfind("\n", 0, index) + 1) + 1
    char = match.group()
    advice = (
        'end lines with "\\n", or write it as "\\r" inside a double-quoted scalar'
        if char == "\r"
        else f'write it as "{portable_escape(char)}" inside a double-quoted scalar'
    )
    raise PortableInputError(
        "yaml_parse_error",
        f"unacceptable character #x{ord(char):04x} at line {line}, column {column}: "
        f"non-printable and line separator characters are not allowed as raw text; {advice}",
    )


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
    # The portable preflight runs first, before any reader is chosen, so a raw character
    # the two runtimes read differently (U+0085, a control, a lone CR) is rejected with
    # one message whether the text would have gone to `json`, to libyaml, or to pure
    # ruamel. Nothing below may see such a text: `json` would keep a raw NEL as content
    # and ruamel would fold it, which is the disagreement the preflight exists to end.
    check_portable_text(text)
    value = _parse_json_subset(text)
    if value is _NOT_JSON:
        return _parse_with_ruamel(text)
    _check_value(value)
    return value


CHECKED_RUAMEL_VERSIONS = ((0, 18), (0, 20))
"""The ruamel.yaml releases, as a ``[lower, upper)`` range, whose reader, scanner and
resolver both fast readers were derived from and compared against.

The JSON path's guards encode where ruamel's YAML 1.2 reading can differ from strict
``json``: its printable set, its line-break set, the 1024-character implicit-key limit.
The C-first guards encode where libyaml accepts what pure ruamel rejects. A later
release could move any of those. Outside this range every text takes pure ruamel, which
costs only speed, instead of keeping a reading that the installed ruamel may no longer
share. Widen the range only after rerunning ``test_json_fast_path.py``,
``test_c_parser.py`` and ``devtools/yaml_parser_fuzz.py`` against the new release.
"""


def _ruamel_is_checked(version: tuple[int, ...] = ruamel.yaml.version_info) -> bool:
    """Whether ``version`` of ruamel.yaml is inside :data:`CHECKED_RUAMEL_VERSIONS`."""
    lower, upper = CHECKED_RUAMEL_VERSIONS
    return lower <= tuple(version[:2]) < upper


PURE_YAML_ENV = "SOFTSCHEMA_PURE_YAML"
"""Environment variable that, set to anything but empty or ``0``, turns off the C parser.

For diagnosis: results are the same either way, so this only changes speed and which
parser :func:`yaml_parser_mode` reports. It is read on every parse.
"""

CHECKED_LIBYAML_VERSION = "0.1.7"
"""The libyaml build, as ``ruamel.yaml.clib`` reports it, that the C-first guards were
derived for and searched against.

Every ``ruamel.yaml.clib`` release so far reports this string, so the check cannot tell
clib releases apart, and it is the clib release that varies between installs: its
maintainer patches the bundled libyaml. The searches behind the guards ran on clib 0.2.8
(with ruamel.yaml 0.18.10) and 0.2.15 (with 0.19.1); a new clib release needs
``devtools/yaml_parser_fuzz.py`` rerun even when this string is unchanged.

:func:`_needs_pure_parser` lists the shapes on which this libyaml accepts what pure
ruamel rejects, or reads a different value. Another libyaml build could add a shape, so
the C parser is used only when it is this build on a checked ruamel release
(:data:`CHECKED_RUAMEL_VERSIONS`); :func:`yaml_parser_mode` reports ``"pure"`` otherwise.
Widen either only after rerunning ``devtools/yaml_parser_fuzz.py`` and
``test_c_parser.py`` against the new build.
"""


def _c_parser_is_checked() -> bool:
    """Whether ruamel found a C parser, and it is the build the guards were derived for."""
    return _installed_libyaml_version() == CHECKED_LIBYAML_VERSION and _ruamel_is_checked()


def _installed_libyaml_version() -> str | None:
    """The libyaml version of the C parser ruamel found, or ``None`` without one.

    ``CParser.__module__`` is ``ruamel.yaml.clib._ruamel_yaml`` on recent clib releases and
    ``_ruamel_yaml`` on older ones; ruamel itself imports the latter name, so it is the
    fallback when the qualified name is not registered.
    """
    parser = YAML(typ="safe").Parser
    if parser is RuamelParser:
        return None
    module = sys.modules.get(parser.__module__) or sys.modules.get("_ruamel_yaml")
    return _libyaml_version(module)


def yaml_parser_reason() -> str:
    """Why :func:`yaml_parser_mode` answers as it does, in one sentence for ``doctor``."""
    ruamel_version = ".".join(map(str, ruamel.yaml.version_info[:3]))
    libyaml = _installed_libyaml_version()
    if libyaml is None:
        return "ruamel.yaml.clib is not installed"
    if libyaml != CHECKED_LIBYAML_VERSION:
        return f"libyaml {libyaml} is not the checked build {CHECKED_LIBYAML_VERSION}"
    if not _ruamel_is_checked():
        lower, upper = CHECKED_RUAMEL_VERSIONS
        return (
            f"ruamel.yaml {ruamel_version} is outside the checked releases "
            f"{lower[0]}.{lower[1]} to {upper[0]}.{upper[1] - 1}"
        )
    if not _c_parser_active():
        return f"turned off by {PURE_YAML_ENV}"
    return f"ruamel.yaml.clib (libyaml {libyaml}) with ruamel.yaml {ruamel_version}"


def _libyaml_version(module: Any) -> str | None:
    """The libyaml version a ``ruamel.yaml.clib`` module reports, or ``None``."""
    get_version_string = getattr(module, "get_version_string", None)
    version = get_version_string() if callable(get_version_string) else None
    return version if isinstance(version, str) else None


_C_PARSER_AVAILABLE = _c_parser_is_checked()
"""Whether :func:`parse_yaml` may use ruamel's C extension (``ruamel.yaml.clib``) at all."""


def yaml_parser_mode() -> Literal["c-first", "pure"]:
    """Which ruamel parser :func:`parse_yaml` reads YAML with, at the time of the call.

    ``"c-first"`` means ruamel's C extension (``ruamel.yaml.clib``) is installed, is the
    libyaml build the guards were checked against on a checked ruamel release
    (:data:`CHECKED_LIBYAML_VERSION`, :data:`CHECKED_RUAMEL_VERSIONS`), and is not turned
    off with ``SOFTSCHEMA_PURE_YAML``: texts are read by libyaml where it is known to agree
    with pure ruamel, and by pure ruamel otherwise. ``"pure"`` means every text is read by
    pure ruamel: the extension is absent, is another build or release, or is turned off.
    The build check happens once at import; the environment variable is read on every
    call, so setting it later changes the answer. Results are identical in both modes;
    only speed differs. :func:`yaml_parser_reason` says which case applies.
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

_SPACE_ONLY_LINE = re.compile(r"(?:\r\n?|\n)( ++)(?=\r|\n)")
"""A line of only spaces, which is where a block scalar can read differently (below).

The search finds these lines first and then looks at the line before each one. The
possessive ``++`` means the engine never retries a shorter run of spaces, so the search
is one pass over the text. Such lines are not rare: an editor that keeps indentation on
blank lines writes one for every blank line inside a literal block, so the work per
line has to stay constant (see :func:`_block_scalar_before_space_line`).
"""

_BLOCK_HEADER_AT_LINE_END = re.compile(r"[|>][-+0-9]{0,2}(?: ++#| *+\Z)")
"""A block scalar header ending a line: ``|`` or ``>``, up to two indicator characters,
then only spaces, or a space and a comment.

libyaml rejects a header with more than two indicators, so ``{0,2}`` loses nothing.
Each ``|`` or ``>`` costs only the spaces after it, never the rest of the line, which
keeps a line full of ``| #`` linear.
"""


def _block_scalar_before_space_line(text: str) -> bool:
    """Whether a block scalar header is followed by a line of only spaces.

    When such a line has fewer spaces than a later leading line, pure ruamel reports "more
    indented follow up line than first in a block scalar"; libyaml reads the scalar.

    The backward search for the start of the line before each match is bounded by the
    start of the previous match, the break that ended the line before it, so each
    space-only line costs the length of the one line before it. Searching from 0 instead made the
    whole text quadratic in the number of space-only lines: in an LF-only text the search
    for ``\\r`` found nothing and scanned back to the start every time.
    """
    low = 0
    for match in _SPACE_ONLY_LINE.finditer(text):
        line_end = match.start()
        line_start = max(text.rfind("\n", low, line_end), text.rfind("\r", low, line_end)) + 1
        if _BLOCK_HEADER_AT_LINE_END.search(text, line_start, line_end) is not None:
            return True
        # The break that starts this match ends the line before the next one, so the next
        # search can stop here (not at ``match.end()``, which for consecutive space-only
        # lines is where the next match starts, leaving nothing to find and a scan from 0).
        low = line_end
    return False


_ROOT_BLOCK_SCALAR = re.compile(r"(?:[ \r\n]++|#[^\r\n]*+|(?:---|\.\.\.)(?=[ \r\n]|\Z))*+[|>]")
"""A document that is a block scalar, after any blank lines, comments and markers.

Its content may start at column zero, where libyaml reads a ``#`` line as a comment and
pure ruamel as content.

Every quantifier is possessive (``++``, ``*+``): a run of whitespace, a comment to the
end of its line, or a marker is consumed once and never split. Without that, the
pattern's nested repetition tried every way of splitting each comment line before
failing on an ordinary document, which doubled the cost with every ``#`` in a leading
banner comment. One consequence: a ``|`` or ``>`` inside a comment is part of the
comment, as it should be, and no longer routes the text to pure ruamel.
"""

_FLOW_VALUE_COLON = re.compile(r":(?<=[ \r\n\"']:)(?![ \r\n])")
"""A colon after a space, line break or quote, before anything but a space or line break.

In a flow sequence pure ruamel, following YAML 1.2, reads such a colon as a mapping
value indicator only when a space or line break follows it, while libyaml reads every
colon in a flow collection as one. So libyaml accepts ``["a":1]``, ``["k"  :v]`` and an
explicit key such as ``[? "a"\\n:x]`` or ``[? a #c\\n:x]``, all of which pure ruamel
rejects. A colon attached to anything but a quote is safe to leave: after a plain scalar
libyaml rejects it, and after a collection, an alias, a tag or nothing the key is not a
string, which the preflight or :func:`_check_value` rejects, so the fallback runs.
The pattern starts at the colon, so the search skips ahead from colon to colon.
"""

_DOCUMENT_END = re.compile(r"\.\.\.(?=[ \r\n]|\Z)(?<![^\r\n]\.\.\.)")
"""A document end marker, ``...`` at the start of a line.

libyaml skips any number of them after a document; pure ruamel reads a second one as
the start of a document with no content, and rejects the text.
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

    Each check is a substring test or a single pass over the text: the regexes either
    start at a literal character and skip ahead between candidates, or use possessive
    quantifiers so that nothing is rescanned, and the space-line check visits each line
    of only spaces once and looks back only as far as the line before it. The cost is
    linear in the text, plus one Python step per space-only line, and a few percent of a
    C parse. ``test_c_parser.py`` pins the routing of adversarial inputs such as a long
    ``#`` banner, a line of thousands of ``| #`` and a block scalar with a hundred thousand
    indented blank lines, counts the characters the space-line loop hands to ``rfind``
    and the header search (at most three per character of text, whatever the input),
    and, in the ``slow`` tier, times the growth of the whole guard.
    """
    if "\t" in text:
        return True
    if not text.isascii() and any(char in text for char in _PURE_ONLY_CHARACTERS):
        return True
    if "%" in text and (text.startswith("%") or "\n%" in text or "\r%" in text):
        return True
    if _BLOCK_HEADER_COMMENT.search(text) is not None:
        return True
    if (" \n" in text or " \r" in text) and _block_scalar_before_space_line(text):
        return True
    if _FLOW_VALUE_COLON.search(text) is not None:
        return True
    if "..." in text and _DOCUMENT_END.search(text) is not None:
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


_BLANK_AFTER_FIRST = ("", " ", "\t")
"""What may follow a node's first character for the ``yaml`` package to keep the indent of
the line before (a block indicator such as ``- `` looks like this)."""


class _FlowIndentation:
    """Reject a flow continuation line in block context that is not indented past its parent.

    YAML 1.2 requires every later line of a flow collection or a quoted scalar that sits
    in block context to be indented, with spaces, past the block collection holding it,
    so ``key: [a,\n b]`` under an indented key, or a tab that indents such a line, is not
    YAML. The ``yaml`` package enforces this ("Missing closing quote", "Flow sequence in
    block collection must be sufficiently indented") and ruamel does not, so these
    documents passed in Python and failed in TypeScript. Python now rejects the same
    lines, mirroring the ``yaml`` lexer's rule rather than the grammar's where the two
    differ: the required indent is the parent's column plus one, or the column of the
    line the node starts on when that is less and the node's first character is followed
    by a non-blank; a blank line, and a comment line inside a flow collection, may have any
    indent; the outermost closing bracket may sit one column short; a root flow node, as
    in a JSON document, has no required indent.

    Fed the events of one parse, in order. Only multi-line nodes are examined, so a
    document without them costs a few comparisons per event.
    """

    def __init__(self, text: str) -> None:
        self._text = text
        self._lines: list[str] | None = None
        self._blocks: list[int] = []
        """Columns of the open block collections, innermost last."""
        self._flow_depth = 0
        self._flow: tuple[int, int] | None = None
        """Required indent and first line of the open outermost flow collection."""
        self._quoted: list[tuple[int, int]] = []
        """First and last lines of the multi-line quoted scalars inside that collection."""

    def collection_start(self, event: MappingStartEvent | SequenceStartEvent) -> None:
        if self._flow_depth:
            self._flow_depth += 1
        elif event.flow_style:
            self._flow_depth = 1
            self._flow = (self._required(event.start_mark), event.start_mark.line)
            self._quoted = []
        else:
            self._blocks.append(event.start_mark.column)

    def collection_end(self, event: MappingEndEvent | SequenceEndEvent) -> None:
        if not self._flow_depth:
            if self._blocks:
                self._blocks.pop()
            return
        self._flow_depth -= 1
        if self._flow_depth or self._flow is None:
            return
        required, first = self._flow
        self._flow = None
        if required and event.end_mark.line > first:
            self._check_flow(required, first, event.end_mark.line, event.end_mark.column - 1)

    def scalar(self, event: ScalarEvent) -> None:
        if event.style not in ('"', "'") or event.end_mark.line == event.start_mark.line:
            return
        if self._flow_depth:
            self._quoted.append((event.start_mark.line, event.end_mark.line))
            return
        required = self._required(event.start_mark)
        for number in range(event.start_mark.line + 1, event.end_mark.line + 1):
            self._check_quoted_line(required, number)

    def _line(self, number: int) -> str:
        if self._lines is None:
            self._lines = self._text.split("\n")
        line = self._lines[number]
        return line[:-1] if line.endswith("\r") else line

    def _required(self, mark: Any) -> int:
        if not self._blocks:
            return 0
        required = self._blocks[-1] + 1
        line = self._line(mark.line)
        column = mark.column
        if not line[:column].strip(" ") and line[column + 1 : column + 2] not in _BLANK_AFTER_FIRST:
            required = min(required, column)
        return required

    def _check_quoted_line(self, required: int, number: int) -> None:
        line = self._line(number)
        spaces = len(line) - len(line.lstrip(" "))
        if spaces < required and spaces < len(line):
            raise self._error(required, number, spaces)

    def _check_flow(self, required: int, first: int, last: int, closing: int) -> None:
        quoted = {number for start, stop in self._quoted for number in range(start + 1, stop + 1)}
        for number in range(first + 1, last + 1):
            if number in quoted:
                self._check_quoted_line(required, number)
                continue
            line = self._line(number)
            spaces = len(line) - len(line.lstrip(" "))
            rest = line[spaces:].lstrip(" \t")
            if not rest or rest[0] == "#" or spaces >= required:
                continue
            if (
                spaces == required - 1
                and number == last
                and rest[0] in "]}"
                and len(line) - len(rest) == closing
            ):
                continue
            raise self._error(required, number, spaces)

    @staticmethod
    def _error(required: int, number: int, spaces: int) -> PortableInputError:
        return PortableInputError(
            "yaml_parse_error",
            f"insufficient indentation at line {number + 1}, column {spaces + 1}: a later line "
            "of a flow collection or quoted scalar in block context must be indented past its "
            f"parent with spaces (at least {required}), or one YAML engine cannot read it",
        )


def _parse_with(text: str, *, pure: bool) -> Any:
    """Parse YAML after a representation preflight, both through the same parser.

    ``pure=False`` selects ruamel's C parser when it is installed. The preflight's event
    pass and the load use one ``YAML`` handle, so they always run on the same parser.
    """
    yaml = YAML(typ="safe", pure=pure)
    yaml.Constructor = _PortableConstructor
    stack: list[tuple[str, bool]] = []
    has_alias = False
    indentation = _FlowIndentation(text)

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
                indentation.scalar(event)
            elif isinstance(event, (MappingStartEvent, SequenceStartEvent)):
                consume_parent_slot()
                stack.append(
                    ("map", True) if isinstance(event, MappingStartEvent) else ("seq", False)
                )
                if len(stack) > MAX_DEPTH:
                    raise PortableInputError("yaml_limit", "YAML nesting exceeds the depth limit")
                indentation.collection_start(event)
            elif isinstance(event, (MappingEndEvent, SequenceEndEvent)):
                stack.pop()
                indentation.collection_end(event)
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
            if type(value) is _NegativeZero:
                raise PortableInputError("number_negative_zero", "negative zero is not supported")
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


def _json_path_enabled(version: tuple[int, ...]) -> bool:
    """Whether the JSON path may run: the installed ruamel is a release the path was
    checked against.

    Outside :data:`CHECKED_RUAMEL_VERSIONS` every text takes the ruamel path. The C
    extension does not matter here: :func:`_parse_with_ruamel` reads every text as pure
    ruamel does with or without it, so the comparison the JSON path rests on holds in
    both modes. A pure function of its input, so the tests can pin the gate.
    """
    return _ruamel_is_checked(version)


_JSON_PATH_ENABLED = _json_path_enabled(ruamel.yaml.version_info)
"""Whether this process runs the JSON path; see :func:`_json_path_enabled`."""

_JSON_ROOT = re.compile(r"[ \n\r]*[\[{]")
"""A root JSON array or object, preceded by whitespace that ruamel also skips.

ruamel skips a tab only inside a flow collection, so a tab before the root is a YAML
error although JSON calls it whitespace; :func:`_parse_json_subset` checks the text
after the root the same way. Space and line breaks are whitespace to both. A scalar
root is left to ruamel: it is cheap there and rare.

Inside the root, the JSON path admits a raw tab in any gap between tokens, at the start
of a line included. That rests on one line of ruamel's scanner, ``scan_to_next_token``:
``white_space = ' \\t' if self.flow_level > 0 else ' '``, so between flow tokens a tab is
whitespace to ruamel exactly as it is to ``json``. YAML 1.2 itself is stricter about
tabs, which makes this the most ruamel-specific assumption of the path;
``test_tabs_between_flow_tokens_are_whitespace_to_ruamel`` pins it by name.
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

_JSON_NEGATIVE_ZERO = re.compile(r"-0(?![.eE0-9])")
"""An integer ``-0``, which ``json`` reads as ``0`` and the spec rejects as negative zero.

Strict JSON spells an integer zero with a minus sign only this way. The pattern also
matches ``-0`` inside a string, which only costs that text the fast path; ruamel's
reading marks the literal for :func:`_check_value`.
"""


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

    - every text, on a ruamel release outside :data:`CHECKED_RUAMEL_VERSIONS`
      (:data:`_JSON_PATH_ENABLED`);
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
    - an integer ``-0`` (:data:`_JSON_NEGATIVE_ZERO`), which ``json`` reads as ``0``;
    - nesting past :data:`MAX_DEPTH`, which ruamel's preflight reports as ``yaml_limit``.

    The tests in ``test_json_fast_path.py`` check each of these against ruamel and
    compare both paths over generated documents built to hit them.
    """
    if not _JSON_PATH_ENABLED or _JSON_ROOT.match(text) is None:
        return _NOT_JSON
    try:
        value = json.loads(text, object_pairs_hook=_json_object, parse_constant=_json_constant)
    except (_NotPortableJson, ValueError, RecursionError):
        return _NOT_JSON
    if "\t" in text[len(text.rstrip(_JSON_WHITESPACE)) :]:
        return _NOT_JSON
    if _json_has_unsafe_character(text) or _JSON_SURROGATE_ESCAPE.search(text):
        return _NOT_JSON
    if "-0" in text and _JSON_NEGATIVE_ZERO.search(text):
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
    This is the difference from :func:`read_frontmatter_doc`, which splits on ``"\n"``,
    drops each line's trailing ``"\r"``, and rejoins with ``"\n"``: fine for reading
    values, lossy for writing the file back.
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
    if first is None or not is_fence_line(text[: first[0]]):
        return None
    metadata_offset = first[1]
    cursor = metadata_offset
    while cursor < len(text):
        line = _line_end(text, cursor)
        if line is None:
            break  # unreachable: the loop guard guarantees a line remains
        if is_fence_line(text[cursor : line[0]]):
            metadata_text = text[metadata_offset:cursor]
            # An empty block (end fence on the very next line) is the portable
            # no_frontmatter case, the same as the reader's ``end == 1``.
            if not metadata_text.strip(" \t\r\n"):
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
    return first is not None and is_fence_line(text[: first[0]])


def is_fence_line(line: str) -> bool:
    """Whether one line, given without its ``\\n``, is a frontmatter ``---`` fence.

    The spec allows ``---`` plus optional trailing whitespace, and *whitespace* here is
    the ASCII blank set, space and tab, after a trailing ``\\r`` is dropped. This is spelled
    out because the two hosts' default trims disagree: ``str.rstrip()`` strips U+0085 and
    U+001C through U+001F, which ``String.prototype.trimEnd()`` keeps, and ``trimEnd()`` strips
    U+FEFF, which ``rstrip()`` keeps. A fence line is never handed to the preflight (it is
    outside the YAML block), so the fence scan is the one place such a character decides a
    verdict; with the default trims a ``---`` followed by U+0085 opened a fence in Python
    and no fence in TypeScript. Keep this identical to ``isFenceLine`` in ``portable.ts``.
    """
    if line.endswith("\r"):
        line = line[:-1]
    return line.rstrip(" \t") == "---"


def _line_end(text: str, start: int) -> tuple[int, int] | None:
    """The content end (before the line break) and the start of the next line.

    A final line with no trailing newline is a line. Its content ends at EOF, and the
    "next line" starts there too, so a caller that keeps scanning stops on the next
    iteration.

    That has to be so, because :func:`read_frontmatter_doc` splits on ``"\n"`` and
    ``readFrontmatterDoc`` with ``split(/\r?\n/)``, and both keep such a line. A scan
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


class _RoundTripRepresenter(RoundTripRepresenter):
    """Round-trip representer overrides scoped to softschema emitter instances.

    ``add_representer`` is a classmethod that writes into the receiving class's registry.
    Called through a stock ``YAML(typ="rt")`` instance, it edits ruamel's shared
    ``RoundTripRepresenter``, and with it every round-trip emitter in the process — a host
    application's own included. A subclass copies the inherited registry on its first
    registration, so the override never reaches other round-trip emitters in the process:
    only the instances :func:`round_trip_yaml` builds spell a null as ``null``.
    """


_RoundTripRepresenter.add_representer(
    type(None),
    lambda dumper, _data: dumper.represent_scalar("tag:yaml.org,2002:null", "null"),
)


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
    yaml.Representer = _RoundTripRepresenter
    yaml.preserve_quotes = True
    yaml.width = 4096  # never re-wrap an author's long line
    yaml.indent(mapping=2, sequence=4, offset=2)
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
