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

from softschema._portable import parse_yaml, read_utf8
from softschema.models import _check_contract_id

JsonPointer = str

_X_SOFTSCHEMA = "x-softschema"


@dataclass(frozen=True)
class FieldInfo:
    """One leaf-ish property in a compiled JSON Schema bundle.

    `pointer` is a JSON Pointer (RFC 6901) relative to the root schema document.
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
        self._schema = deepcopy(schema)

    @classmethod
    def load(cls, schema_path: Path) -> SchemaView:
        """Load a compiled YAML or JSON schema from disk."""
        data = parse_yaml(read_utf8(schema_path))
        if not isinstance(data, dict):
            msg = f"schema at {schema_path} is not a mapping at the root"
            raise ValueError(msg)
        return cls(data)

    @property
    def raw(self) -> dict[str, Any]:
        """The full underlying schema dict. Treat as read-only."""
        return deepcopy(self._schema)

    @property
    def root_softmeta(self) -> dict[str, Any]:
        """The root-level `x-softschema` block (empty dict if absent)."""
        meta = self._schema.get(_X_SOFTSCHEMA)
        return dict(meta) if isinstance(meta, dict) else {}

    @property
    def contract_id(self) -> str | None:
        """Validated logical contract ID from `x-softschema.contract`."""
        meta_contract = self.root_softmeta.get("contract")
        if isinstance(meta_contract, str):
            return _check_contract_id(meta_contract)
        return None

    @property
    def schema_id(self) -> str | None:
        """JSON Schema resource identity, separate from the artifact contract."""
        value = self._schema.get("$id")
        return value if isinstance(value, str) else None

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

        Raises `KeyError` when the pointer does not resolve.
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
        # JSON Schema 2020-12 also allows `anyOf: [{$ref: ...}, {type: null}]` for
        # optional refs (which Pydantic emits). Handle both.
        if not isinstance(ref, str):
            ref = _ref_from_anyof(prop)
        if not isinstance(ref, str) or ref in seen_refs:
            return prop, None
        target = _resolve_ref(self._schema, ref)
        if target is None:
            return prop, None
        merged = dict(target)
        merged.update({key: value for key, value in prop.items() if key != "$ref"})
        return merged, ref


def _ref_from_anyof(prop: dict[str, Any]) -> str | None:
    branch = _nullable_value_branch(prop)
    ref = branch.get("$ref") if branch is not None else None
    return ref if isinstance(ref, str) else None


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
    t = prop.get("type")
    if isinstance(t, str):
        return t
    if isinstance(t, list) and len(t) == 2 and t.count("null") == 1:
        # JSON Schema 2020-12 allows ["string", "null"] etc. Return the non-null one.
        non_null = [entry for entry in t if entry != "null"]
        if len(non_null) == 1 and isinstance(non_null[0], str):
            return non_null[0]
    # `anyOf` style optionals (Pydantic's `Foo | None`): extract from the first typed branch.
    branch = _nullable_value_branch(prop)
    if branch is not None:
        inner = branch.get("type")
        if isinstance(inner, str) and inner != "null":
            return inner
    return None


def _extract_enum(prop: dict[str, Any]) -> list[str] | None:
    enum = prop.get("enum")
    if isinstance(enum, list) and all(isinstance(v, str) for v in enum):
        return list(enum)
    # `anyOf: [{enum: [...]}, {type: null}]` shape from `Literal[...] | None`.
    branch = _nullable_value_branch(prop)
    if branch is not None:
        inner = branch.get("enum")
        if isinstance(inner, list) and all(isinstance(v, str) for v in inner):
            return list(inner)
    return None


def _nullable_value_branch(prop: dict[str, Any]) -> dict[str, Any] | None:
    any_of = prop.get("anyOf")
    if not isinstance(any_of, list) or len(any_of) != 2:
        return None
    nulls = [entry for entry in any_of if entry == {"type": "null"}]
    others = [entry for entry in any_of if isinstance(entry, dict) and entry != {"type": "null"}]
    return others[0] if len(nulls) == 1 and len(others) == 1 else None


def _extract_softmeta(prop: dict[str, Any]) -> dict[str, Any]:
    meta = prop.get(_X_SOFTSCHEMA)
    return dict(meta) if isinstance(meta, dict) else {}


def _escape_pointer_segment(segment: str) -> str:
    return segment.replace("~", "~0").replace("/", "~1")


def _unescape_pointer_segment(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")
