"""Bounded UTF-8 and portable YAML input shared by artifact and schema reads."""

from __future__ import annotations

import math
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


def read_utf8(path: Path) -> str:
    """Read one UTF-8 artifact."""
    try:
        return path.read_bytes().decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PortableInputError("invalid_utf8", "input is not valid UTF-8") from exc


def parse_yaml(text: str) -> Any:
    """Parse YAML with the existing library after a representation preflight."""
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

    Returns ``None`` when the document has no frontmatter, matching what
    :func:`read_frontmatter_doc` reports: no leading fence, an unterminated fence, or an
    empty block whose end fence is the very next line.

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
            return None  # unterminated fence: no frontmatter to speak of
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
    return None


def _line_end(text: str, start: int) -> tuple[int, int] | None:
    """The content end (before the line break) and the start of the next line."""
    index = text.find("\n", start)
    if index == -1:
        return None
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
