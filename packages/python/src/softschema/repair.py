"""Syntactic repair for YAML an agent wrote by hand.

A program emitting YAML has a serializer in the path, and every serializer quotes a value
that would otherwise change meaning. An agent writing frontmatter by hand has no such
thing, so it produces a narrow, recognizable family of mistakes: an unquoted ``: `` inside
a note (``summary: Note: actually Q1``), or a value that opens with a quoted phrase and
then keeps going (``"near me" trends accelerated``). Both make the whole document
unparsable, which means nothing downstream can read any of it — a total loss over one
character.

This module puts quotes back where the missing serializer would have, and nothing else.
It runs before any schema is consulted, because a document that does not parse has no
values to validate.

**Scope.** This is for artifacts an agent just emitted. Running it over human-authored or
program-generated YAML hides a real bug: if your code writes invalid YAML, fix the writer.

**Why the self-check uses softschema's own reader.** The obvious implementation checks
its work with a plain YAML parse. That is not enough here, because
:func:`~softschema._portable.parse_yaml` enforces rules an ordinary parser does not —
aliases and anchors rejected, merge keys, explicit tags, non-string mapping keys, a depth
bound, the safe-integer range. A repair judged by the looser parser would report success
and then fail validation seconds later, which is the exact failure this module exists to
prevent, moved one layer up.

**What is deliberately not repaired.** Several portable violations look like parse
failures and are not typos: an alias, a merge key, an explicit tag. Each is something the
author meant, and quoting cannot fix any of them. They pass through with their original
error code so the caller reports the real problem instead of a failed repair.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from softschema._portable import (
    PortableInputError,
    find_non_portable_character,
    parse_yaml,
    portable_escape,
    read_utf8,
    split_frontmatter,
    write_artifact_text,
)
from softschema.models import SchemaProfile

REPAIR_KIND = "repair_applied"
"""``kind`` on every record this module emits.

Repairs are reported with the same ``kind``/``code``/``path`` surface as errors, so a
caller matches what was fixed the way it matches what failed. See the spec, "Matching on
structural error records".
"""

_YAML_QUOTED_SCALAR = "yaml_quoted_scalar"
"""``code`` for a plain scalar quoted because YAML read structure in it."""

_YAML_ESCAPED_CHARACTER = "yaml_escaped_character"
"""``code`` for a value rewritten as a double-quoted scalar to escape a rejected character.

The portable preflight refuses a raw U+0085, U+2028, U+2029, control character or lone
carriage return anywhere in the YAML text. Inside a single-line value the fix is
mechanical and meaning-preserving: a serializer would have written the escape, and the
decoded value is exactly what YAML 1.2 gives the raw text. The character itself is never
replaced by a guess at what was meant (a mis-decoded ellipsis stays a U+0085, now visible
in the record); and a rejected character in a key, a comment or a block scalar has no such
rewrite, so those stay parse errors.
"""

# Portable violations that are not authoring slips. Quoting a scalar cannot fix any of
# them, and attempting a repair would replace a precise diagnostic with a vague one.
_NOT_REPAIRABLE = frozenset(
    {
        "yaml_alias",
        "yaml_merge_key",
        "yaml_custom_tag",
        "yaml_non_string_key",
        "yaml_duplicate_key",
        "yaml_limit",
        "yaml_unsupported_scalar",
        "number_out_of_range",
        "number_negative_zero",
        "invalid_utf8",
    }
)

# A mapping line: indent, key, `: `, then the value. The indent is optional, unlike the
# upstream version this is ported from, which required it. Every payload there sits under
# an envelope so its keys are always indented; here the frontmatter root and the whole
# pure-yaml profile put keys at column 0.
#
# The character class is spelled out rather than using `\w`, which is Unicode-aware in
# Python and ASCII-only in JavaScript — the two implementations must agree on which keys
# they will touch, and the conservative ASCII set is the pinned choice (a non-ASCII key is
# left unrepaired identically on both sides; the shared vectors lock this in).
_MAPPING_LINE = re.compile(r"^(?P<indent>[ \t]*)(?P<key>[A-Za-z0-9_.-]+): (?P<value>.+)$")

# A line that opens a block scalar (`key: |`, `"quoted": >-`, `- |2`, `- key: |`, with an
# optional comment): its content is every following line indented deeper than the opener,
# and the escaping rule must not touch those lines even when one looks like `key: value`.
# The opener is recognised by the indicator alone, whatever the key looks like, so a quoted
# or non-ASCII key opens a block scalar here exactly as it does for the engines.
_BLOCK_SCALAR_OPENER = re.compile(
    r"^[ \t]*(?:-[ \t]+)?(?:[^\n]*?:[ \t]+)?[|>][-+0-9]*[ \t]*(?:#[^\n]*)?$"
)
_TRAILING_COMMENT = re.compile(r"^[ \t]*(?:#[^\n]*)?$")

# Characters that cannot begin a plain scalar (YAML 1.2 c-indicator). A value starting
# with one is a flow collection, a comment, an anchor, an alias, a tag, a block scalar
# indicator, or a directive, never a plain scalar, so neither pass may quote it: the quotes
# would turn structure into a string. `-`, `?` and `:` are indicators only when followed
# by a space or standing alone.
_NOT_PLAIN_START = frozenset("[]{}#&*!|>'\"%@`")


def _can_be_plain_scalar(stripped: str) -> bool:
    if not stripped or stripped[0] in _NOT_PLAIN_START:
        return False
    return not (stripped[0] in "-?:" and (len(stripped) == 1 or stripped[1] in " \t"))


@dataclass(frozen=True)
class RepairResult:
    """What one repair attempt did.

    ``ok`` says the document parses now — which it may have done all along. ``changed``
    says this pass rewrote something. The two are independent: an untouched valid
    document is ``ok`` and unchanged, and a document too broken to fix is neither.
    """

    ok: bool
    changed: bool
    text: str | None = None
    records: list[dict[str, Any]] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


def _record(path: list[Any], detail: str, code: str = _YAML_QUOTED_SCALAR) -> dict[str, Any]:
    return {
        "kind": REPAIR_KIND,
        "code": code,
        "path": path,
        "message": detail,
    }


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _closing_quote(text: str, quote: str) -> int | None:
    """Index of the quote that closes the scalar opened at ``text[0]``, or ``None``.

    Inside double quotes a backslash escapes the next character; inside single quotes the
    only escape is a doubled quote.
    """
    index = 1
    while index < len(text):
        char = text[index]
        if quote == '"' and char == "\\":
            index += 2
            continue
        if char == quote:
            if quote == "'" and text[index + 1 : index + 2] == "'":
                index += 2
                continue
            return index
        index += 1
    return None


def _escape_characters(text: str) -> str:
    return re.sub(
        r".", lambda m: portable_escape(m.group()) if _is_rejected(m.group()) else m.group(), text
    )


def _is_rejected(char: str) -> bool:
    return find_non_portable_character(char) is not None


def _follows_open_escape(body: str) -> bool:
    """Whether a rejected character in a double-quoted body follows an unescaped backslash.

    There the character is the second half of an escape the author started: ``\\`` and a
    raw NEL is a YAML 1.1 escaped line break, and ``\\`` and a raw control character is no
    escape at all. No rewrite keeps a value the text never had, and escaping the character
    as well would write ``\\\\`` and the escape's name as text while reporting success.
    The value is left for the author. A backslash that is itself escaped (``\\\\``)
    does not count.
    """
    backslashes = 0
    for char in body:
        if char == "\\":
            backslashes += 1
            continue
        if backslashes % 2 and _is_rejected(char):
            return True
        backslashes = 0
    return False


def _escape_value(value: str) -> tuple[str, list[str]] | None:
    """Rewrite a single-line value holding a rejected character as a double-quoted scalar.

    Returns the new value text and the characters escaped, or ``None`` when the value has
    nothing to escape or is not one of the three shapes this rule can rewrite exactly: a
    plain scalar, a complete single-quoted scalar, or a complete double-quoted scalar, each
    optionally followed by a comment. Whitespace before a comment is kept as written. The
    decoded value is unchanged in every case: the plain and single-quoted forms are
    re-expressed with the same content, and in the double-quoted form only the raw
    characters are replaced, so escapes the author already wrote stay as they are.
    """
    if find_non_portable_character(value) is None:
        return None
    # A lone carriage return is a line break for YAML 1.2 and for ruamel, so the text after
    # it may be another line of the document; escaping it as content would swallow that
    # line. It stays a parse error, whose message already says to end lines with "\n".
    if "\r" in value:
        return None
    # Only ASCII blanks are trimmed: `str.strip()` would also eat the U+0085 being escaped.
    stripped = value.strip(" \t")
    if stripped[:1] in {'"', "'"}:
        quote = stripped[0]
        end = _closing_quote(stripped, quote)
        if end is None or not _TRAILING_COMMENT.match(stripped[end + 1 :]):
            return None
        body, rest = stripped[1:end], stripped[end + 1 :]
        if quote == '"' and _follows_open_escape(body):
            return None
        if quote == "'":
            body = body.replace("''", "'").replace("\\", "\\\\").replace('"', '\\"')
    else:
        if not _can_be_plain_scalar(stripped):
            return None  # a flow collection, comment, anchor, alias or tag: not a scalar
        comment = re.search(r"([ \t]+#[^\n]*)$", stripped)
        body = stripped[: comment.start()] if comment else stripped
        rest = comment.group(1) if comment else ""
        body = body.replace("\\", "\\\\").replace('"', '\\"')
    escaped = sorted({char for char in body if _is_rejected(char)}, key=ord)
    if not escaped:
        return None  # the rejected character sits in the comment, which has no escape
    return f'"{_escape_characters(body)}"{rest}', escaped


def _escape_detail(key: str, escaped: list[str]) -> str:
    listed = ", ".join(f'#x{ord(char):04x} as "{portable_escape(char)}"' for char in escaped)
    return f"escaped {listed} in the value of {key!r}"


def _value_needs_quoting(value: str) -> bool:
    """Whether a plain scalar carries something YAML will read as structure.

    Two shapes matter. A second ``: `` makes the parser look for a nested mapping where
    the author meant prose. A leading quote that never closes makes it try to read a
    quoted scalar and run off the end of the value.
    """
    # Only ASCII blanks are trimmed and only `[ \t]+#[ \t]` opens a comment: the hosts'
    # default whitespace sets differ (U+0085 is whitespace to Python, U+FEFF to JavaScript),
    # and a rejected character trimmed away here would be dropped from the file silently.
    stripped = value.strip(" \t")
    if (stripped.startswith('"') and stripped.endswith('"')) or (
        stripped.startswith("'") and stripped.endswith("'")
    ):
        return False
    if stripped in ("null", "true", "false", "~", ""):
        return False
    if stripped[0] not in {'"', "'"} and not _can_be_plain_scalar(stripped):
        return False  # a flow collection or other non-scalar: `: ` inside it is structure
    comment = re.search(r"[ \t]+#[ \t]", stripped)
    value_part = stripped[: comment.start()] if comment else stripped
    if ": " in value_part:
        return True
    return _starts_with_unbalanced_quoted_phrase(value_part)


def _starts_with_unbalanced_quoted_phrase(value: str) -> bool:
    """True for a scalar like ``"foo" bar``.

    The value as a whole is not a quoted scalar, but its leading quote makes the parser
    try to read one. Quoting the whole thing and escaping the inner quotes is the least
    invasive fix.
    """
    return (
        len(value) >= 2
        and value[0] in {'"', "'"}
        and not value.endswith(value[0])
        and value[0] in value[1:]
    )


def _quote_value(value: str) -> str:
    """Wrap a value in double quotes, leaving any trailing comment outside them.

    The whitespace before a comment is carried over exactly rather than normalized to one
    space. Collapsing it is a restyling change on a line this pass was only asked to quote,
    and a fix that quietly reformats what it touches is how a one-scalar diff becomes a
    reviewable-looking whole-file one.
    """
    stripped = value.strip(" \t")
    comment = re.search(r"([ \t]+#[ \t][^\n]*)$", stripped)
    if comment:
        value_part = stripped[: comment.start()]
        comment_part = comment.group(1)
    else:
        value_part = stripped
        comment_part = ""
    escaped = value_part.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"{comment_part}'


def repair_yaml_text(text: str) -> RepairResult:
    """Repair one YAML region: the frontmatter block, or a whole pure-yaml document.

    Parses first and returns unchanged when the text is already portable, so a valid
    document is never rewritten. When the parse fails for a reason quoting could plausibly
    address, quotes the offending scalars and re-parses. A repair that does not produce a
    portable document is discarded, and the original failure is what the caller reports.
    """
    try:
        parse_yaml(text)
    except PortableInputError as exc:
        if exc.code in _NOT_REPAIRABLE:
            return RepairResult(
                ok=False, changed=False, error_code=exc.code, error_message=str(exc)
            )
        original_code, original_message = exc.code, str(exc)
    else:
        return RepairResult(ok=True, changed=False, text=text)

    repaired_lines: list[str] = []
    records: list[dict[str, Any]] = []
    block_indent: int | None = None
    for line in text.split("\n"):
        if block_indent is not None:
            # Inside a block scalar: content runs while lines are blank or indented deeper
            # than the opener. The escaping rule leaves it alone, whatever it looks like.
            if line.strip(" \t") == "" or _indent_of(line) > block_indent:
                repaired_lines.append(line)
                continue
            block_indent = None
        if _BLOCK_SCALAR_OPENER.match(line):
            block_indent = _indent_of(line)
            repaired_lines.append(line)
            continue
        match = _MAPPING_LINE.match(line)
        if match:
            key, value = match.group("key"), match.group("value")
            escaped = _escape_value(value)
            if escaped is not None:
                repaired_lines.append(f"{match.group('indent')}{key}: {escaped[0]}")
                records.append(
                    _record([key], _escape_detail(key, escaped[1]), _YAML_ESCAPED_CHARACTER)
                )
                continue
            if _value_needs_quoting(value):
                repaired_lines.append(f"{match.group('indent')}{key}: {_quote_value(value)}")
                records.append(_record([key], f"quoted the value of {key!r}"))
                continue
        repaired_lines.append(line)

    if not records:
        return RepairResult(
            ok=False, changed=False, error_code=original_code, error_message=original_message
        )

    repaired = "\n".join(repaired_lines)
    try:
        parse_yaml(repaired)
    except PortableInputError:
        # Quoting did not make the document portable. Report what was actually wrong
        # rather than the residue of a failed guess.
        return RepairResult(
            ok=False, changed=False, error_code=original_code, error_message=original_message
        )
    return RepairResult(ok=True, changed=True, text=repaired, records=records)


def repair_artifact(
    path: Path,
    *,
    profile: SchemaProfile = SchemaProfile.frontmatter_md,
    write: bool = True,
) -> RepairResult:
    """Repair one artifact on disk.

    For ``frontmatter-md`` only the fenced block is touched and the body is spliced back
    by offset, so it survives byte-for-byte. For ``pure-yaml`` the whole document is the
    region.

    ``write=False`` reports what would change without touching the file, which is what
    ``repair --dry-run`` and ``repair --check`` run on.

    ``text`` on the result is the full document, repaired or not, so a caller that is
    about to conform and validate does not read the file a second time.
    """
    try:
        content = read_utf8(path)
    except OSError as exc:
        return RepairResult(
            ok=False, changed=False, error_code="artifact_unreadable", error_message=str(exc)
        )
    except PortableInputError as exc:
        return RepairResult(ok=False, changed=False, error_code=exc.code, error_message=str(exc))

    # ruamel and the line scan below both work in `\n`; a CRLF document is normalized for
    # the duration and restored on the way out, so repairing one scalar does not silently
    # convert every line ending in the file.
    crlf = "\r\n" in content
    normalized = content.replace("\r\n", "\n") if crlf else content

    if profile is SchemaProfile.pure_yaml:
        result = repair_yaml_text(normalized)
        repaired_document = result.text
    else:
        split = split_frontmatter(normalized)
        if split is None:
            # No frontmatter is not a repair failure; it is a validation verdict, and
            # validation owns reporting it.
            return RepairResult(ok=True, changed=False, text=content)
        result = repair_yaml_text(split.metadata_text)
        # Splice by offset: everything outside the metadata region — the opening fence,
        # the closing fence, and the whole body — comes back verbatim rather than
        # re-synthesized, so a repair cannot restyle anything it did not fix.
        repaired_document = (
            None
            if result.text is None
            else normalized[: split.metadata_offset]
            + result.text
            + normalized[split.metadata_end : split.body_offset]
            + normalized[split.body_offset :]
        )

    if repaired_document is not None and crlf:
        repaired_document = repaired_document.replace("\n", "\r\n")

    if not result.changed:
        return RepairResult(
            ok=result.ok,
            changed=False,
            text=repaired_document if result.ok else content,
            error_code=result.error_code,
            error_message=result.error_message,
        )

    if write and repaired_document is not None:
        write_artifact_text(path, repaired_document)
    return RepairResult(ok=True, changed=True, text=repaired_document, records=result.records)
