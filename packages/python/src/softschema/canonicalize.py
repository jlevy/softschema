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

# Applicators whose subschemas each contribute *part* of one instance's constraints
# rather than describing it completely. A fragment is never closed internally: its
# `properties` is a partial contribution (or, for `if`, a matcher rather than a
# declaration), so closing it would reject keys a sibling fragment declares, or stop a
# conditional from firing at all. Their contributions are closed at the composition
# root instead, with annotation-aware `unevaluatedProperties`.
#
# `anyOf`/`oneOf` are deliberately absent: an alternative branch describes the instance
# completely, so it closes on its own terms (the compiled shape of an optional model
# field is `anyOf: [{$ref: ...}, {"type": "null"}]`).
_FRAGMENT_APPLICATORS = frozenset({"allOf", "if", "then", "else", "not", "dependentSchemas"})

# Definition keywords reset the fragment flag: a definition is a complete declaration
# reached by `$ref`, so it closes on its own terms even when the reference sits inside a
# fragment.
_DEFINITION_KEYWORDS = frozenset({"$defs", "definitions"})

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

    Under ``enforced`` the schema is authoritative at the boundary: an object schema
    that declares properties but is silent about closure is validated as closed. Three
    clauses decide where and how, because a schema that *composes* constraints cannot be
    closed the same way as one that declares them in a single place:

    1. Closure is never injected inside a fragment subtree
       (``allOf``/``if``/``then``/``else``/``not``/``dependentSchemas``). A fragment
       contributes part of an instance's constraints, so closing it would reject keys a
       sibling fragment declares; closing an ``if`` matcher would silently stop the
       conditional from firing. ``$defs`` resets this — a definition is a complete
       declaration reached by ``$ref``.
    2. A node declares properties if it carries ``properties``, *or* if a fragment
       applicator under it does. The second half matters: a schema may declare every
       property inside its ``allOf`` branches, and would otherwise be enforced nowhere.
    3. Such a node is closed with ``unevaluatedProperties: false`` when it carries a
       fragment applicator, and ``additionalProperties: false`` otherwise.
       ``unevaluatedProperties`` is annotation-aware, so properties evaluated by
       ``properties``, by an ``allOf`` branch, by a successful ``if``, by ``then``,
       ``else``, ``dependentSchemas``, or through ``$ref`` all count as declared, and
       only genuinely undeclared keys fail.

    An explicit ``additionalProperties`` or ``unevaluatedProperties`` (``true``,
    ``false``, or a subschema) always wins, so a schema can opt specific objects out of
    strictness. Object schemas that declare no properties anywhere (free-form mappings
    such as ``dict[str, X]``) are unaffected.

    One consequence of annotation-aware closure is worth knowing: a property named in an
    ``if`` matcher is *evaluated* when the matcher succeeds, so it is admitted. Given
    ``if: {properties: {secret: {const: "x"}}}`` and no ``secret`` in the root's
    ``properties``, ``{"secret": "x"}`` passes closure while ``{"secret": "other"}`` is
    rejected. That is correct 2020-12 behavior and the price of the annotation model.

    This is a validation-time overlay applied by ``validate_structural`` when the
    effective status is ``enforced``. It never changes compiled schemas.
    """
    result = _apply_enforced_extras(schema, in_fragment=False)
    assert isinstance(result, dict)
    return result


def _apply_enforced_extras(node: Any, *, in_fragment: bool) -> Any:
    if not isinstance(node, dict):
        return node

    out: dict[str, Any] = {}
    for key, value in node.items():
        # A definition is a complete declaration, so it closes even inside a fragment.
        child_fragment = False if key in _DEFINITION_KEYWORDS else in_fragment
        child_fragment = child_fragment or key in _FRAGMENT_APPLICATORS
        if key in _NAME_MAP_KEYWORDS and isinstance(value, dict):
            out[key] = {
                name: _apply_enforced_extras(sub, in_fragment=child_fragment)
                for name, sub in value.items()
            }
        elif key in _SCHEMA_LIST_KEYWORDS and isinstance(value, list):
            out[key] = [_apply_enforced_extras(item, in_fragment=child_fragment) for item in value]
        elif key in _SCHEMA_KEYWORDS:
            out[key] = _apply_enforced_extras(value, in_fragment=child_fragment)
        else:
            out[key] = value

    if in_fragment:
        return out
    if "additionalProperties" in out or "unevaluatedProperties" in out:
        return out
    has_fragment = any(key in _FRAGMENT_APPLICATORS for key in out)
    if isinstance(out.get("properties"), dict):
        out["unevaluatedProperties" if has_fragment else "additionalProperties"] = False
    elif has_fragment and _fragment_declares_properties(out):
        out["unevaluatedProperties"] = False
    return out


def _fragment_declares_properties(node: dict[str, Any]) -> bool:
    """Whether a fragment applicator under ``node`` declares ``properties``.

    Recurses through fragment applicators only. A ``$ref`` is not followed: it is not a
    lexical declaration, and the definition it names closes on its own terms.
    """
    return any(
        _declares_properties(value) for key, value in node.items() if key in _FRAGMENT_APPLICATORS
    )


def _declares_properties(node: Any) -> bool:
    if isinstance(node, list):
        return any(_declares_properties(item) for item in node)
    if not isinstance(node, dict):
        return False
    if isinstance(node.get("properties"), dict):
        return True
    return _fragment_declares_properties(node)
