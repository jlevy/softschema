"""Bounded UTF-8 and portable YAML input shared by artifact and schema reads."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any

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
        raise PortableInputError("invalid_utf8", f"`{path}`: input is not valid UTF-8") from exc
    return text[1:] if text.startswith(BOM) else text


_NON_PORTABLE_CHARACTER = re.compile(
    "[^\t\n\r\x20-\x7e\xa0-\u2027\u202a-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]"
)
"""A raw character the two YAML engines read differently.

The class is YAML 1.2 ``c-printable`` with the three Unicode line separators taken out.
ruamel rejects everything outside ``c-printable`` (its ``Reader.NON_PRINTABLE``) and the
``yaml`` package reads it as content; for U+0085, U+2028 and U+2029 ruamel follows YAML
1.1 and treats them as line breaks, folding a NEL in a flow scalar to a space and breaking
a block scalar or a comment into a parse error, while the ``yaml`` package again reads
them as content. Neither reading can be reproduced in the other engine, so the portable
rule is to accept none of them raw. Every one of them can be written as a double-quoted
escape (``"\\f"``, ``"\\x7f"``, ``"\\N"``, ``"\\L"``, ``"\\P"``), which both engines decode
identically. Keep this class identical to ``NON_PORTABLE_CHARACTER`` in ``portable.ts``.
"""


def check_portable_text(text: str) -> None:
    """Reject the first raw character in ``text`` that the engines would read differently.

    Runs before the engine sees the text, on the whole YAML text the reader was handed:
    the frontmatter block or the entire pure-yaml document, comments and keys included.
    The line and column are counted within that text, as the engines count them. Raising
    here, with one message in both runtimes, is what keeps a mis-decoded cp1252 ellipsis
    (which arrives as U+0085) from silently becoming a space in one runtime and staying a
    character in the other.
    """
    match = _NON_PORTABLE_CHARACTER.search(text)
    if match is None:
        return
    index = match.start()
    line = text.count("\n", 0, index) + 1
    column = index - (text.rfind("\n", 0, index) + 1) + 1
    raise PortableInputError(
        "yaml_parse_error",
        f"unacceptable character #x{ord(match.group()):04x} at line {line}, column {column}: "
        "non-printable and line separator characters are not allowed as raw text; "
        "write one as a double-quoted escape",
    )


def parse_yaml(text: str) -> Any:
    """Parse YAML with the existing library after a representation preflight."""
    check_portable_text(text)
    yaml = YAML(typ="safe")
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
