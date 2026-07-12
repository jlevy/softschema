"""Canonical JSON Schema profile shared by every softschema implementation.

`model_json_schema()` (Pydantic) and `z.toJSONSchema()` (Zod) emit the same
contract in incidentally different shapes. To make the compiled schema
content-identical across languages (so a Pydantic-compiled and a Zod-compiled
schema share the same ``schema_sha256`` over the canonical JSON), both
compilers run their raw output through :func:`canonicalize_json_schema` before
serialization.

The transforms are intentionally minimal and semantic:

1. **Named-object extraction into ``$defs``** is a *precondition*, not a
   transform here: Pydantic already extracts nested models into ``$defs`` and
   the Zod compiler must request the matching shape with ``reused: "inline"``
   (which extracts only id-registered named objects into ``$defs`` rather than
   any repeated subschema). This function asserts nothing about it and simply
   preserves whatever ``$defs`` exist.
2. **Nullable unions are ``anyOf``.** A ``oneOf``/``anyOf`` that is exactly a
   type plus ``{"type": "null"}`` is normalized to ``anyOf`` (Pydantic's form;
   Zod emits ``oneOf`` for ``.nullable()``).
3. **Annotations are preserved.** ``title``, ``default``, descriptions, and unknown
   extension data are never rewritten by canonicalization.
4. **Required fields are sorted.** Their order does not affect validation, so the
   stable form does not depend on model declaration order. Enum order remains authored.

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


def _is_string_key_constraint(value: Any) -> bool:
    return isinstance(value, dict) and list(value.keys()) == ["type"] and value["type"] == "string"


# Keywords whose value is a mapping of arbitrary *names* to subschemas. Their
# keys are field/definition names (which may legitimately be "title" or
# "default") and must be preserved; only their values are subschemas.
_NAME_MAP_KEYWORDS = frozenset(
    {"properties", "$defs", "definitions", "patternProperties", "dependentSchemas"}
)

# Keywords whose value is a list of subschemas.
_SCHEMA_LIST_KEYWORDS = frozenset({"anyOf", "oneOf", "allOf", "prefixItems"})

# Keywords whose value is a single subschema (when it is a mapping).
_SCHEMA_KEYWORDS = frozenset(
    {
        "items",
        "additionalProperties",
        "unevaluatedProperties",
        "unevaluatedItems",
        "not",
        "if",
        "then",
        "else",
        "contains",
        "propertyNames",
        "contentSchema",
    }
)


def canonicalize_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a canonicalized copy of ``schema`` (see module docstring)."""
    return _canonicalize_schema(schema)


def _canonicalize_schema(node: Any) -> Any:
    """Canonicalize one schema object, recursing only into subschema positions.

    Annotation and unknown values are preserved verbatim.
    """
    if not isinstance(node, dict):
        return node
    node = _normalize_nullable_union(node)
    out: dict[str, Any] = {}
    for key, value in node.items():
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


def apply_enforced_extras(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``schema`` with the ``status: enforced`` strictness overlay.

    Under ``enforced`` the schema is authoritative at the boundary: every object
    schema that declares ``properties`` but is silent about
    ``additionalProperties`` is validated as ``additionalProperties: false``.
    An explicit ``additionalProperties`` (``true``, ``false``, or a subschema)
    always wins, so a schema can opt specific objects out of strictness.
    Object schemas without ``properties`` (free-form mappings such as
    ``dict[str, X]``) are unaffected.

    This is a validation-time overlay applied by ``validate_structural`` when the
    effective status is ``enforced``. It never changes compiled schemas.
    """
    result = _apply_enforced_extras(schema)
    assert isinstance(result, dict)
    return result


class EnforcementUnsupportedError(ValueError):
    """The requested closure would change composed-schema meaning."""


def _apply_enforced_extras(node: Any) -> Any:
    if not isinstance(node, dict):
        return node
    union = node.get("allOf")
    if isinstance(union, list) and any(_contains_open_properties(branch) for branch in union):
        raise EnforcementUnsupportedError(
            "enforced closure is unsupported for allOf object composition"
        )
    dependent = node.get("dependentSchemas")
    if isinstance(dependent, dict) and any(
        _contains_open_properties(branch) for branch in dependent.values()
    ):
        raise EnforcementUnsupportedError(
            "enforced closure is unsupported for dependent object composition"
        )
    if any(_contains_open_properties(node.get(key)) for key in ("if", "then", "else", "not")):
        raise EnforcementUnsupportedError(
            "enforced closure is unsupported for conditional object composition"
        )
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key in _NAME_MAP_KEYWORDS and isinstance(value, dict):
            out[key] = {name: _apply_enforced_extras(sub) for name, sub in value.items()}
        elif key in _SCHEMA_LIST_KEYWORDS and isinstance(value, list):
            out[key] = [_apply_enforced_extras(item) for item in value]
        elif key in _SCHEMA_KEYWORDS:
            out[key] = _apply_enforced_extras(value)
        else:
            out[key] = value
    if isinstance(out.get("properties"), dict) and "additionalProperties" not in out:
        out["additionalProperties"] = False
    return out


def _contains_open_properties(node: Any) -> bool:
    if not isinstance(node, dict):
        return False
    if isinstance(node.get("properties"), dict) and "additionalProperties" not in node:
        return True
    for key, value in node.items():
        if key in _SCHEMA_KEYWORDS and _contains_open_properties(value):
            return True
        if (
            key in _SCHEMA_LIST_KEYWORDS
            and isinstance(value, list)
            and any(_contains_open_properties(item) for item in value)
        ):
            return True
        if (
            key in _NAME_MAP_KEYWORDS
            and isinstance(value, dict)
            and any(_contains_open_properties(item) for item in value.values())
        ):
            return True
    return False
