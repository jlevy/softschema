"""Read-only view over a compiled JSON Schema.

`SchemaView` is the single navigation API for downstream consumers (QA rules,
agent prompts, comparison logic, generated sections). Having one reader prevents
each consumer from re-implementing JSON Schema traversal and accidentally
diverging on edge cases like `$ref` resolution or `x-softschema` lookup.
"""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from softschema.models import validate_contract_id, validate_schema_id
from softschema.value_domain import (
    DEFAULT_VALIDATION_LIMITS,
    ValidationLimits,
    parse_portable_yaml,
)

JsonPointer = str

_X_SOFTSCHEMA = "x-softschema"
_ANNOTATION_KEYWORDS = frozenset(
    {
        "$comment",
        "contentEncoding",
        "contentMediaType",
        "default",
        "deprecated",
        "description",
        "examples",
        "format",
        "readOnly",
        "title",
        "writeOnly",
        _X_SOFTSCHEMA,
    }
)
_NULL_SCHEMA_KEYWORDS = _ANNOTATION_KEYWORDS | {"type"}
_REFERENCE_SCHEMA_KEYWORDS = _ANNOTATION_KEYWORDS | {"$ref"}


@dataclass(frozen=True)
class FieldInfo:
    """One leaf-ish property in a compiled JSON Schema bundle.

    `pointer` is a JSON Pointer (RFC 6901) relative to the root schema document.
    `json_type` and `enum` are ``None`` when the field is a genuine union rather
    than one exact nullable value shape.
    `softmeta` is the field's per-property `x-softschema` block (empty dict when
    the field was not annotated with `SoftField`).
    """

    pointer: JsonPointer
    name: str
    json_type: str | None
    enum: list[str] | None
    required: bool
    description: str | None
    softmeta: dict[str, Any] = field(default_factory=dict)


class SchemaView:
    """Stable navigation API over a compiled JSON Schema 2020-12 file with x-softschema."""

    def __init__(self, schema: dict[str, Any]) -> None:
        """Snapshot an already normalized JSON-compatible schema mapping."""
        self._schema = deepcopy(schema)

    @classmethod
    def load(
        cls,
        schema_path: Path,
        *,
        limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
    ) -> SchemaView:
        """Load a compiled YAML or JSON schema through the portable-value boundary.

        Raises ``OSError`` for an unreadable path, ``UnicodeDecodeError`` for invalid
        UTF-8, a portable-YAML error for invalid or out-of-domain YAML, and
        ``ValueError`` when the parsed root is not a mapping.
        """
        encoded = schema_path.read_bytes()
        data = parse_portable_yaml(
            encoded.decode("utf-8-sig"),
            limits=limits,
            encoded_size=len(encoded),
        )
        if not isinstance(data, dict):
            msg = f"schema at {schema_path} is not a mapping at the root"
            raise ValueError(msg)
        return cls(data)

    @property
    def raw(self) -> dict[str, Any]:
        """Return a defensive deep copy of the schema snapshot."""
        return deepcopy(self._schema)

    @property
    def root_softmeta(self) -> dict[str, Any]:
        """The root-level `x-softschema` block (empty dict if absent)."""
        meta = self._schema.get(_X_SOFTSCHEMA)
        return deepcopy(meta) if isinstance(meta, dict) else {}

    @property
    def contract_id(self) -> str | None:
        """Validated contract ID, including the legacy-0.2 ``$id`` fallback."""
        meta_contract = self.root_softmeta.get("contract")
        if isinstance(meta_contract, str):
            try:
                return validate_contract_id(meta_contract)
            except ValueError:
                return None
        schema_id = self._schema.get("$id")
        if isinstance(schema_id, str):
            try:
                return validate_contract_id(schema_id)
            except ValueError:
                pass
        return None

    @property
    def schema_id(self) -> str | None:
        """Validated JSON Schema resource ID, separate from the logical contract ID."""
        schema_id = self._schema.get("$id")
        if isinstance(schema_id, str):
            try:
                return validate_schema_id(schema_id)
            except ValueError:
                pass
        return None

    @property
    def schema_sha256(self) -> str | None:
        """The `x-softschema.schema_sha256` hash (None if the compiled schema has none)."""
        value = self.root_softmeta.get("schema_sha256")
        return value if isinstance(value, str) else None

    def iter_fields(self, *, include_refs: bool = True) -> Iterable[FieldInfo]:
        """Yield one `FieldInfo` per property reachable from the schema root.

        `include_refs=True` (the default) follows `$ref`s into `$defs`, so a
        nested `MoviePage` object yields each of its leaf-ish properties under
        their full JSON-Pointer path. Cycles are detected and skipped.
        """
        yield from self._walk(self._schema, "", set(), include_refs=include_refs)

    def field(self, pointer: JsonPointer) -> FieldInfo:
        """Resolve a JSON Pointer to a single `FieldInfo`.

        Raises ``ValueError`` when the pointer does not resolve.
        """
        for info in self.iter_fields():
            if info.pointer == pointer:
                return info
        msg = f"no field at pointer {pointer!r}"
        raise ValueError(msg)

    def enum_values(self, pointer: JsonPointer) -> list[str] | None:
        """Return the `enum` list at `pointer`, or None if it has none."""
        return self.field(pointer).enum

    def softmeta(self, pointer: JsonPointer) -> dict[str, Any]:
        """Return the `x-softschema` block at `pointer` (empty dict if absent)."""
        return dict(self.field(pointer).softmeta)

    def fields_by_group(self, group: str) -> list[FieldInfo]:
        return [f for f in self.iter_fields() if f.softmeta.get("group") == group]

    def fields_by_owner(self, owner: str) -> list[FieldInfo]:
        return [f for f in self.iter_fields() if f.softmeta.get("owner") == owner]

    def fields_by_tier(self, tier: str) -> list[FieldInfo]:
        return [f for f in self.iter_fields() if f.softmeta.get("tier") == tier]

    def _walk(
        self,
        node: dict[str, Any],
        base_pointer: str,
        seen_refs: set[str],
        *,
        include_refs: bool,
    ) -> Iterable[FieldInfo]:
        properties = node.get("properties")
        if not isinstance(properties, dict):
            return
        required_set = set(node.get("required") or [])
        for name, raw_prop in properties.items():
            if not isinstance(raw_prop, dict):
                continue
            prop, ref = self._maybe_resolve_ref(raw_prop, seen_refs, include_refs=include_refs)
            pointer = f"{base_pointer}/properties/{_escape_pointer_segment(name)}"
            yield FieldInfo(
                pointer=pointer,
                name=name,
                json_type=_extract_type(prop),
                enum=_extract_enum(prop),
                required=name in required_set,
                description=prop.get("description"),
                softmeta=_extract_softmeta(prop),
            )
            # Recurse into nested objects (after the ref is resolved). Carry the
            # just-followed $ref down the recursion path so a cyclic schema
            # (A -> B -> A) terminates. The augmented set is scoped to this path only,
            # so a $def reused by sibling fields (e.g. Address) still expands under each.
            if include_refs and prop.get("properties"):
                next_seen = seen_refs | {ref} if ref is not None else seen_refs
                yield from self._walk(prop, pointer, next_seen, include_refs=include_refs)

    def _maybe_resolve_ref(
        self,
        prop: dict[str, Any],
        seen_refs: set[str],
        *,
        include_refs: bool,
    ) -> tuple[dict[str, Any], str | None]:
        if not include_refs:
            return prop, None
        ref = prop.get("$ref")
        ref_branch: dict[str, Any] | None = None
        if isinstance(ref, str):
            if not set(prop).issubset(_REFERENCE_SCHEMA_KEYWORDS):
                return prop, None
        else:
            nullable_ref = _exact_nullable_ref(prop, self._schema)
            if nullable_ref is None:
                return prop, None
            ref, ref_branch = nullable_ref
        if ref in seen_refs:
            return prop, None
        target = _resolve_ref(self._schema, ref)
        if target is None:
            return prop, None
        merged = dict(target)
        for source in (ref_branch, prop):
            if source is not None:
                merged.update(
                    {key: value for key, value in source.items() if key in _ANNOTATION_KEYWORDS}
                )
        return merged, ref


def _exact_nullable_ref(
    prop: dict[str, Any],
    root: dict[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    branch = _exact_nullable_value_branch(prop)
    if branch is None or not set(branch).issubset(_REFERENCE_SCHEMA_KEYWORDS):
        return None
    ref = branch.get("$ref")
    if not isinstance(ref, str):
        return None
    target = _resolve_ref(root, ref)
    if target is None or not _schema_excludes_null(target, root, set()):
        return None
    return ref, branch


def _exact_nullable_value_branch(prop: dict[str, Any]) -> dict[str, Any] | None:
    present = [keyword for keyword in ("anyOf", "oneOf") if keyword in prop]
    if len(present) != 1:
        return None
    if not set(prop).issubset(_ANNOTATION_KEYWORDS | {present[0]}):
        return None
    union = prop.get(present[0])
    if not isinstance(union, list) or len(union) != 2:
        return None
    null_indexes = [index for index, entry in enumerate(union) if _is_exact_null_schema(entry)]
    if len(null_indexes) != 1:
        return None
    branch = union[1 - null_indexes[0]]
    return branch if isinstance(branch, dict) else None


def _is_exact_null_schema(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("type") == "null"
        and set(value).issubset(_NULL_SCHEMA_KEYWORDS)
    )


def _schema_excludes_null(
    schema: dict[str, Any],
    root: dict[str, Any],
    seen_refs: set[str],
) -> bool:
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        return schema_type != "null"
    if isinstance(schema_type, list) and schema_type:
        return "null" not in schema_type
    enum = schema.get("enum")
    if isinstance(enum, list):
        return None not in enum
    if "const" in schema:
        return schema["const"] is not None
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref not in seen_refs:
        target = _resolve_ref(root, ref)
        if target is not None:
            return _schema_excludes_null(target, root, {*seen_refs, ref})
    for keyword in ("anyOf", "oneOf"):
        union = schema.get(keyword)
        if isinstance(union, list) and union:
            return all(
                isinstance(branch, dict) and _schema_excludes_null(branch, root, seen_refs)
                for branch in union
            )
    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        return any(
            isinstance(branch, dict) and _schema_excludes_null(branch, root, seen_refs)
            for branch in all_of
        )
    return False


def _resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any] | None:
    """Resolve a local `#/$defs/Name` or `#/...` JSON Pointer reference."""
    if not ref.startswith("#/"):
        return None
    cur: Any = schema
    for segment in ref[2:].split("/"):
        segment = _unescape_pointer_segment(segment)
        if isinstance(cur, dict) and segment in cur:
            cur = cur[segment]
        else:
            return None
    return cur if isinstance(cur, dict) else None


def _extract_type(prop: dict[str, Any]) -> str | None:
    if "$ref" in prop:
        return None
    t = prop.get("type")
    if isinstance(t, str):
        return t
    if isinstance(t, list):
        # Report one type only when the array is exactly that type, optionally nullable.
        non_null = [entry for entry in t if isinstance(entry, str) and entry != "null"]
        if (
            all(isinstance(entry, str) for entry in t)
            and len(t) in (1, 2)
            and len(set(t)) == len(t)
            and len(non_null) == 1
        ):
            return non_null[0]
    branch = _exact_nullable_value_branch(prop)
    if branch is not None:
        inner = branch.get("type")
        if isinstance(inner, str) and inner != "null":
            return inner
    return None


def _extract_enum(prop: dict[str, Any]) -> list[str] | None:
    if "$ref" in prop:
        return None
    enum = prop.get("enum")
    if isinstance(enum, list) and all(isinstance(v, str) for v in enum):
        return list(enum)
    branch = _exact_nullable_value_branch(prop)
    if branch is not None:
        inner = branch.get("enum")
        if isinstance(inner, list) and all(isinstance(v, str) for v in inner):
            return list(inner)
    return None


def _extract_softmeta(prop: dict[str, Any]) -> dict[str, Any]:
    meta = prop.get(_X_SOFTSCHEMA)
    return deepcopy(meta) if isinstance(meta, dict) else {}


def _escape_pointer_segment(segment: str) -> str:
    return segment.replace("~", "~0").replace("/", "~1")


def _unescape_pointer_segment(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")
