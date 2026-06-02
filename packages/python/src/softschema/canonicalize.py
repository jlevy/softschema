"""Canonical JSON Schema profile shared by every softschema implementation.

`model_json_schema()` (Pydantic) and `z.toJSONSchema()` (Zod) emit the same
contract in incidentally different shapes. To make the compiled sidecar
byte-identical across languages — so a Pydantic-compiled and a Zod-compiled
sidecar share the same ``schema_sha256`` — both compilers run their raw output
through :func:`canonicalize_json_schema` before serialization.

The transforms are intentionally minimal and semantic:

1. **Named-object extraction into ``$defs``** is a *precondition*, not a
   transform here: Pydantic already extracts nested models into ``$defs`` and
   the Zod compiler must request the same (``reused: "ref"``). This function
   asserts nothing about it and simply preserves whatever ``$defs`` exist.
2. **Nullable unions are ``anyOf``.** A ``oneOf``/``anyOf`` that is exactly a
   type plus ``{"type": "null"}`` is normalized to ``anyOf`` (Pydantic's form;
   Zod emits ``oneOf`` for ``.nullable()``).
3. **Auto-generated ``title`` keys are dropped.** Pydantic adds a ``title`` to
   every property and ``$def``; Zod adds none. softschema does not author
   titles, so the canonical profile omits them entirely.
4. **Implicit ``default: null`` is stripped.** Pydantic emits ``default: null``
   for ``X | None = None`` fields; the canonical profile omits a null default.
   Non-null defaults are preserved.

Key ordering (rule 5 in the design) is handled at serialization time
(frontmatter-format's YAML writer with ``key_sort`` and ``json.dumps(...,
sort_keys=True)`` for the hash), so it is not a transform here.
"""

from __future__ import annotations

from typing import Any

# JavaScript Number.MIN_SAFE_INTEGER / MAX_SAFE_INTEGER, which Zod's z.int() emits as
# minimum/maximum for otherwise-unbounded integers. Stripped so the canonical form is
# free of language-specific integer bounds.
_JS_MIN_SAFE_INTEGER = -9007199254740991
_JS_MAX_SAFE_INTEGER = 9007199254740991


def _is_empty_default(value: Any) -> bool:
    return value is None or value == [] or value == {}


def _is_string_key_constraint(value: Any) -> bool:
    return isinstance(value, dict) and list(value.keys()) == ["type"] and value["type"] == "string"


# Keywords whose value is a mapping of arbitrary *names* to subschemas. Their
# keys are field/definition names (which may legitimately be "title" or
# "default") and must be preserved; only their values are subschemas.
_NAME_MAP_KEYWORDS = frozenset({"properties", "$defs", "definitions", "patternProperties"})

# Keywords whose value is a list of subschemas.
_SCHEMA_LIST_KEYWORDS = frozenset({"anyOf", "oneOf", "allOf", "prefixItems"})

# Keywords whose value is a single subschema (when it is a mapping).
_SCHEMA_KEYWORDS = frozenset(
    {"items", "additionalProperties", "not", "if", "then", "else", "contains", "propertyNames"}
)


def canonicalize_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a canonicalized copy of ``schema`` (see module docstring)."""
    return _canonicalize_schema(schema)


def _canonicalize_schema(node: Any) -> Any:
    """Canonicalize one schema object, recursing only into subschema positions.

    ``title`` and a null ``default`` are dropped as *keywords* here, but never
    when they appear as names inside a ``properties``/``$defs`` map.
    """
    if not isinstance(node, dict):
        return node
    node = _normalize_nullable_union(node)
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key == "title":
            continue
        # Drop implicit/empty defaults (null, [], {}); these are no-ops on Pydantic output
        # but normalize Zod's `.default([])`/`.default({})`/nullable defaults.
        if key == "default" and _is_empty_default(value):
            continue
        # Drop JS safe-integer sentinel bounds that Zod's int() adds for unbounded sides.
        if key == "minimum" and value == _JS_MIN_SAFE_INTEGER:
            continue
        if key == "maximum" and value == _JS_MAX_SAFE_INTEGER:
            continue
        # Drop the redundant string-key constraint (z.record); JSON keys are always strings.
        if key == "propertyNames" and _is_string_key_constraint(value):
            continue
        if key == "required" and isinstance(value, list):
            # `required` is a set; sort it so cross-language field-definition order
            # does not affect the canonical bytes.
            out[key] = sorted(value)
            continue
        if key in _NAME_MAP_KEYWORDS and isinstance(value, dict):
            out[key] = {name: _canonicalize_schema(sub) for name, sub in value.items()}
        elif key in _SCHEMA_LIST_KEYWORDS and isinstance(value, list):
            out[key] = [_canonicalize_schema(item) for item in value]
        elif key in _SCHEMA_KEYWORDS:
            out[key] = _canonicalize_schema(value)
        else:
            out[key] = value
    return out


def _normalize_nullable_union(node: dict[str, Any]) -> dict[str, Any]:
    """Rewrite a ``oneOf`` nullable union to the ``anyOf`` form.

    Only the exact "type-or-null" shape is rewritten, so unrelated ``oneOf``
    schemas are left untouched.
    """
    union = node.get("oneOf")
    if not isinstance(union, list) or "anyOf" in node:
        return node
    if not _is_nullable_union(union):
        return node
    rewritten = dict(node)
    del rewritten["oneOf"]
    rewritten["anyOf"] = union
    return rewritten


def _is_nullable_union(union: list[Any]) -> bool:
    if len(union) != 2:
        return False
    has_null = any(isinstance(entry, dict) and entry.get("type") == "null" for entry in union)
    has_other = any(isinstance(entry, dict) and entry.get("type") != "null" for entry in union)
    return has_null and has_other
