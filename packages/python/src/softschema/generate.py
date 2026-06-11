"""Generated schema sections: deterministic Markdown blocks from `SchemaView`.

Marker format:

    <!-- softschema:generated kind="enum_table" schema="schemas/foo.schema.yaml" -->
    ...rendered content...
    <!-- /softschema:generated -->

The renderer parses the attributes from the opening marker, loads the referenced
compiled schema through `SchemaView`, renders the section, and writes the file back.
With ``check=True`` it returns a drift report instead of touching the file, so CI
can fail when committed sections lag behind the schema. The path attribute is
``schema=`` (a file path); the older ``contract=`` spelling is rejected, since a
contract is a logical ID, not a file path.

Kinds shipped in v0.1:

- ``enum_table``: one table row per enum-valued field in the schema.
- ``field_list``: one bullet per field (name, type, required, description).
- ``vocab``: the enum values at a specific JSON Pointer (requires ``pointer=``).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from strif import atomic_write_text

from softschema.schema_view import SchemaView

_MARKER_OPEN = re.compile(
    r"<!--\s*softschema:generated\s+(?P<attrs>[^>]*?)\s*-->",
)
_MARKER_CLOSE = "<!-- /softschema:generated -->"
_ATTR_PATTERN = re.compile(r'(?P<key>[A-Za-z_][A-Za-z0-9_]*)="(?P<value>[^"]*)"')
_KNOWN_ATTRS = frozenset({"kind", "schema", "pointer", "sha256"})
_CONTRACT_ATTR_RENAME = (
    'softschema:generated marker uses the removed "contract" attribute for a schema '
    'path; rename it to "schema" (contract is a logical ID, not a file path)'
)


@dataclass
class GeneratedSection:
    """One parsed marker block from a document."""

    start: int  # offset just after the opening marker (start of content)
    end: int  # offset of the closing marker
    open_marker: str
    close_marker: str
    attrs: dict[str, str]
    existing_content: str

    @property
    def kind(self) -> str:
        return self.attrs.get("kind", "")

    @property
    def schema(self) -> str:
        return self.attrs.get("schema", "")


@dataclass
class RegenerateResult:
    """Outcome of regenerating one document."""

    path: Path
    sections: int = 0
    drift: bool = False
    drift_details: list[str] = field(default_factory=list)


def parse_sections(text: str) -> list[GeneratedSection]:
    """Find every ``softschema:generated`` marker block in ``text``."""
    sections: list[GeneratedSection] = []
    cursor = 0
    while True:
        open_match = _MARKER_OPEN.search(text, cursor)
        if open_match is None:
            return sections
        open_end = open_match.end()
        close_index = text.find(_MARKER_CLOSE, open_end)
        if close_index == -1:
            msg = (
                f"unterminated softschema:generated marker starting at offset {open_match.start()}"
            )
            raise ValueError(msg)
        attrs = _parse_attrs(open_match.group("attrs"))
        existing = text[open_end:close_index]
        sections.append(
            GeneratedSection(
                start=open_end,
                end=close_index,
                open_marker=open_match.group(0),
                close_marker=_MARKER_CLOSE,
                attrs=attrs,
                existing_content=existing,
            )
        )
        cursor = close_index + len(_MARKER_CLOSE)


def regenerate(
    path: Path,
    *,
    check: bool = False,
    schema_root: Path | None = None,
) -> RegenerateResult:
    """Regenerate every ``softschema:generated`` block in ``path``.

    With ``check=True`` the file is not touched; the result reports whether any
    block has drifted from what the schema would currently render.

    ``schema_root`` controls how the ``schema="..."`` attribute is resolved: by
    default a relative path is resolved relative to the file containing the marker.
    """
    text = path.read_text(encoding="utf-8")
    sections = parse_sections(text)
    result = RegenerateResult(path=path, sections=len(sections))
    if not sections:
        return result

    base = schema_root or path.parent
    new_text = ""
    cursor = 0
    for section in sections:
        rendered = _render_section(section, base)
        new_text += text[cursor : section.start] + rendered
        cursor = section.end
        if rendered != section.existing_content:
            result.drift = True
            result.drift_details.append(f"{path}: section {section.attrs.get('kind', '?')} drifted")
    new_text += text[cursor:]

    if not check and result.drift:
        atomic_write_text(path, new_text)
    return result


def _render_section(section: GeneratedSection, schema_root: Path) -> str:
    if "contract" in section.attrs:
        raise ValueError(_CONTRACT_ATTR_RENAME)
    unknown = sorted(key for key in section.attrs if key not in _KNOWN_ATTRS)
    if unknown:
        msg = f"softschema:generated marker has unknown attribute(s): {', '.join(unknown)}"
        raise ValueError(msg)
    if not section.kind:
        msg = f"softschema:generated marker is missing 'kind': {section.open_marker}"
        raise ValueError(msg)
    if not section.schema:
        msg = f"softschema:generated marker is missing 'schema': {section.open_marker}"
        raise ValueError(msg)
    renderer = _RENDERERS.get(section.kind)
    if renderer is None:
        known = ", ".join(sorted(_RENDERERS))
        msg = f"unknown softschema:generated kind {section.kind!r}; known: {known}"
        raise ValueError(msg)
    schema_path = _resolve_schema_path(section.schema, schema_root)
    view = SchemaView.load(schema_path)
    body = renderer(view, section.attrs)
    return f"\n{body}\n"


def _resolve_schema_path(schema: str, base: Path) -> Path:
    path = Path(schema)
    if not path.is_absolute():
        path = base / path
    if not path.exists():
        msg = f"softschema:generated schema not found: {path}"
        raise FileNotFoundError(msg)
    return path


def _render_enum_table(view: SchemaView, attrs: dict[str, str]) -> str:
    lines = ["| Field | Allowed values |", "| --- | --- |"]
    for field_info in view.iter_fields():
        if field_info.enum is None:
            continue
        values = ", ".join(v.replace("|", "\\|") for v in field_info.enum)
        lines.append(f"| `{field_info.name}` | {values} |")
    if len(lines) == 2:
        lines.append("| _(no enum fields)_ | _(none)_ |")
    return "\n".join(lines)


def _render_field_list(view: SchemaView, attrs: dict[str, str]) -> str:
    lines: list[str] = []
    for field_info in view.iter_fields():
        # Only list root-level properties for readability; nested properties show
        # up via their parent's type.
        if field_info.pointer.count("/properties/") > 1:
            continue
        type_label = field_info.json_type or "object"
        required = "required" if field_info.required else "optional"
        description = field_info.description or ""
        if description:
            lines.append(f"- `{field_info.name}` ({type_label}, {required}): {description}")
        else:
            lines.append(f"- `{field_info.name}` ({type_label}, {required})")
    if not lines:
        lines.append("- _(no fields)_")
    return "\n".join(lines)


def _render_vocab(view: SchemaView, attrs: dict[str, str]) -> str:
    pointer = attrs.get("pointer")
    if not pointer:
        msg = "softschema:generated kind=vocab requires a 'pointer' attribute"
        raise ValueError(msg)
    values = view.enum_values(pointer)
    if values is None:
        msg = f"no enum at pointer {pointer!r}"
        raise ValueError(msg)
    return "\n".join(f"- `{v}`" for v in values)


_RENDERERS: dict[str, Callable[[SchemaView, dict[str, str]], str]] = {
    "enum_table": _render_enum_table,
    "field_list": _render_field_list,
    "vocab": _render_vocab,
}


def _parse_attrs(attr_string: str) -> dict[str, str]:
    return {
        match.group("key"): match.group("value") for match in _ATTR_PATTERN.finditer(attr_string)
    }
