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
2. **Nullable unions are ``anyOf``.** A two-branch ``oneOf`` is normalized only
   when one branch is exactly null and the other provably excludes null through
   an explicit type or an internal reference.
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
from urllib.parse import unquote, urldefrag

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

_CHILD_SCHEMA_KEYWORDS = frozenset(
    {
        "items",
        "additionalProperties",
        "unevaluatedProperties",
        "unevaluatedItems",
        "contains",
        "propertyNames",
        "contentSchema",
    }
)

_SAME_INSTANCE_SCHEMA_KEYWORDS = frozenset({"not", "if", "then", "else"})
_SAME_INSTANCE_LIST_KEYWORDS = frozenset({"anyOf", "oneOf", "allOf"})
_NULL_ANNOTATION_KEYWORDS = frozenset(
    {
        "type",
        "title",
        "description",
        "$comment",
        "default",
        "deprecated",
        "readOnly",
        "writeOnly",
        "examples",
    }
)

ENFORCEMENT_UNSUPPORTED_MESSAGE = "enforced validation cannot be applied safely to this schema"


class EnforcementUnsupportedError(ValueError):
    """Raised when the strict overlay cannot preserve a schema's composition semantics."""

    def __init__(self, schema_path: str) -> None:
        super().__init__(ENFORCEMENT_UNSUPPORTED_MESSAGE)
        self.schema_path = schema_path


def canonicalize_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a canonicalized copy of ``schema`` (see module docstring)."""
    result = _canonicalize_schema(schema, schema)
    assert isinstance(result, dict)
    return result


def _canonicalize_schema(node: Any, root: dict[str, Any]) -> Any:
    """Canonicalize one schema object, recursing only into subschema positions.

    ``title`` and a null ``default`` are dropped as *keywords* here, but never
    when they appear as names inside a ``properties``/``$defs`` map.
    """
    if not isinstance(node, dict):
        return node
    node = _normalize_nullable_union(node, root)
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
            out[key] = {name: _canonicalize_schema(sub, root) for name, sub in value.items()}
        elif key in _SCHEMA_LIST_KEYWORDS and isinstance(value, list):
            out[key] = [_canonicalize_schema(item, root) for item in value]
        elif key in _SCHEMA_KEYWORDS:
            out[key] = _canonicalize_schema(value, root)
        else:
            out[key] = value
    return out


def _normalize_nullable_union(
    node: dict[str, Any],
    root: dict[str, Any],
) -> dict[str, Any]:
    """Rewrite a ``oneOf`` nullable union to the ``anyOf`` form.

    Only the exact "type-or-null" shape is rewritten, so unrelated ``oneOf``
    schemas are left untouched.
    """
    union = node.get("oneOf")
    if not isinstance(union, list) or "anyOf" in node:
        return node
    if not _is_nullable_union(union, root):
        return node
    rewritten = dict(node)
    del rewritten["oneOf"]
    rewritten["anyOf"] = union
    return rewritten


def _is_nullable_union(union: list[Any], root: dict[str, Any]) -> bool:
    if len(union) != 2:
        return False
    null_indexes = [index for index, entry in enumerate(union) if _is_exact_null_schema(entry)]
    if len(null_indexes) != 1:
        return False
    other = union[1 - null_indexes[0]]
    return _schema_excludes_null(other, root, set())


def _is_exact_null_schema(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("type") == "null"
        and set(value).issubset(_NULL_ANNOTATION_KEYWORDS)
    )


def _schema_excludes_null(
    value: Any,
    root: dict[str, Any],
    seen: set[int],
) -> bool:
    if not isinstance(value, dict):
        return False
    schema_type = value.get("type")
    if isinstance(schema_type, str):
        return schema_type != "null"
    if isinstance(schema_type, list) and schema_type:
        return "null" not in schema_type
    reference = value.get("$ref")
    if not isinstance(reference, str):
        return False
    target = _resolve_internal_reference(root, reference)
    if not isinstance(target, dict) or id(target) in seen:
        return False
    return _schema_excludes_null(target, root, {*seen, id(target)})


def _resolve_internal_reference(root: dict[str, Any], reference: str) -> Any | None:
    try:
        resource_id, fragment = urldefrag(reference)
    except ValueError:
        return None
    if resource_id and resource_id != root.get("$id"):
        return None
    if not resource_id and not reference.startswith("#") and reference != "":
        return None
    if fragment == "":
        return root
    if not fragment.startswith("/"):
        return None
    try:
        tokens = unquote(fragment[1:]).split("/")
    except UnicodeError:
        return None
    current: Any = root
    for encoded in tokens:
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdecimal() and int(token) < len(current):
            current = current[int(token)]
        else:
            return None
    return current


def apply_enforced_extras(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``schema`` with the ``status: enforced`` strictness overlay.

    Simple object boundaries retain the legacy ``additionalProperties: false``
    overlay. Composed boundaries use ``unevaluatedProperties: false`` so sibling
    applicators can contribute evaluated properties. An explicit value for either
    keyword wins, and free-form mappings remain open.

    This is a validation-time overlay applied by ``validate_structural`` when the
    effective status is ``enforced``. It never changes compiled schemas and raises
    :class:`EnforcementUnsupportedError` rather than partially closing an unsafe
    composition.
    """
    result = _apply_enforced_extras(schema, root=schema, close_boundary=True, path=())
    assert isinstance(result, dict)
    return result


def _apply_enforced_extras(
    node: Any,
    *,
    root: dict[str, Any],
    close_boundary: bool,
    path: tuple[str | int, ...],
) -> Any:
    if not isinstance(node, dict):
        return node
    _check_enforcement_support(node, root, path)
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key in {"properties", "patternProperties"} and isinstance(value, dict):
            out[key] = {
                name: _apply_enforced_extras(
                    sub,
                    root=root,
                    close_boundary=True,
                    path=(*path, key, name),
                )
                for name, sub in value.items()
            }
        elif key in {"$defs", "definitions", "dependentSchemas"} and isinstance(value, dict):
            out[key] = {
                name: _apply_enforced_extras(
                    sub,
                    root=root,
                    close_boundary=False,
                    path=(*path, key, name),
                )
                for name, sub in value.items()
            }
        elif key in _SAME_INSTANCE_LIST_KEYWORDS and isinstance(value, list):
            out[key] = [
                _apply_enforced_extras(
                    item,
                    root=root,
                    close_boundary=False,
                    path=(*path, key, index),
                )
                for index, item in enumerate(value)
            ]
        elif key == "prefixItems" and isinstance(value, list):
            out[key] = [
                _apply_enforced_extras(
                    item,
                    root=root,
                    close_boundary=True,
                    path=(*path, key, index),
                )
                for index, item in enumerate(value)
            ]
        elif key in _CHILD_SCHEMA_KEYWORDS:
            out[key] = _apply_enforced_extras(
                value,
                root=root,
                close_boundary=True,
                path=(*path, key),
            )
        elif key in _SAME_INSTANCE_SCHEMA_KEYWORDS:
            out[key] = _apply_enforced_extras(
                value,
                root=root,
                close_boundary=False,
                path=(*path, key),
            )
        else:
            out[key] = value
    if (
        close_boundary
        and "additionalProperties" not in out
        and "unevaluatedProperties" not in out
        and _object_properties_are_evaluated(node, root, set())
    ):
        _check_static_object_boundary(node, root, path)
        keyword = (
            "unevaluatedProperties"
            if _composition_evaluates_object_properties(node, root)
            else "additionalProperties"
        )
        out[keyword] = False
    return out


def _check_static_object_boundary(
    node: dict[str, Any],
    root: dict[str, Any],
    path: tuple[str | int, ...],
) -> None:
    direct = node.get("properties")
    direct_names = set(direct) if isinstance(direct, dict) else set()
    conditional = node.get("if")
    if _object_properties_are_evaluated(conditional, root, set()):
        conditional_properties = (
            conditional.get("properties") if isinstance(conditional, dict) else None
        )
        if not isinstance(conditional_properties, dict) or not set(conditional_properties).issubset(
            direct_names
        ):
            raise EnforcementUnsupportedError(_json_pointer((*path, "if")))
    dependent = node.get("dependentSchemas")
    if isinstance(dependent, dict):
        for name in dependent:
            if name not in direct_names:
                raise EnforcementUnsupportedError(_json_pointer((*path, "dependentSchemas", name)))


def _check_enforcement_support(
    node: dict[str, Any],
    root: dict[str, Any],
    path: tuple[str | int, ...],
) -> None:
    for keyword in ("$dynamicRef", "$recursiveRef"):
        if keyword in node:
            raise EnforcementUnsupportedError(_json_pointer((*path, keyword)))
    reference = node.get("$ref")
    if isinstance(reference, str) and _resolve_internal_reference(root, reference) is None:
        raise EnforcementUnsupportedError(_json_pointer((*path, "$ref")))
    negated = node.get("not")
    if _contains_enforceable_object(negated, root, set()):
        raise EnforcementUnsupportedError(_json_pointer((*path, "not")))


def _object_properties_are_evaluated(
    node: Any,
    root: dict[str, Any],
    seen: set[int],
) -> bool:
    if not isinstance(node, dict) or id(node) in seen:
        return False
    seen = {*seen, id(node)}
    if isinstance(node.get("properties"), dict) or isinstance(node.get("patternProperties"), dict):
        return True
    reference = node.get("$ref")
    if isinstance(reference, str):
        target = _resolve_internal_reference(root, reference)
        if _object_properties_are_evaluated(target, root, seen):
            return True
    for keyword in _SAME_INSTANCE_LIST_KEYWORDS:
        value = node.get(keyword)
        if isinstance(value, list) and any(
            _object_properties_are_evaluated(item, root, seen) for item in value
        ):
            return True
    for keyword in ("then", "else"):
        if _object_properties_are_evaluated(node.get(keyword), root, seen):
            return True
    dependent = node.get("dependentSchemas")
    return isinstance(dependent, dict) and any(
        _object_properties_are_evaluated(item, root, seen) for item in dependent.values()
    )


def _composition_evaluates_object_properties(
    node: dict[str, Any],
    root: dict[str, Any],
) -> bool:
    reference = node.get("$ref")
    if isinstance(reference, str) and _object_properties_are_evaluated(
        _resolve_internal_reference(root, reference), root, {id(node)}
    ):
        return True
    for keyword in _SAME_INSTANCE_LIST_KEYWORDS:
        value = node.get(keyword)
        if isinstance(value, list) and any(
            _object_properties_are_evaluated(item, root, {id(node)}) for item in value
        ):
            return True
    for keyword in ("then", "else"):
        if _object_properties_are_evaluated(node.get(keyword), root, {id(node)}):
            return True
    dependent = node.get("dependentSchemas")
    return isinstance(dependent, dict) and any(
        _object_properties_are_evaluated(item, root, {id(node)}) for item in dependent.values()
    )


def _contains_enforceable_object(
    node: Any,
    root: dict[str, Any],
    seen: set[int],
) -> bool:
    if not isinstance(node, dict) or id(node) in seen:
        return False
    seen = {*seen, id(node)}
    if _object_properties_are_evaluated(node, root, set()):
        return True
    for keyword in _NAME_MAP_KEYWORDS:
        value = node.get(keyword)
        if isinstance(value, dict) and any(
            _contains_enforceable_object(item, root, seen) for item in value.values()
        ):
            return True
    for keyword in _SCHEMA_LIST_KEYWORDS:
        value = node.get(keyword)
        if isinstance(value, list) and any(
            _contains_enforceable_object(item, root, seen) for item in value
        ):
            return True
    return any(
        _contains_enforceable_object(node.get(keyword), root, seen) for keyword in _SCHEMA_KEYWORDS
    )


def _json_pointer(path: tuple[str | int, ...]) -> str:
    return "".join(f"/{str(part).replace('~', '~0').replace('/', '~1')}" for part in path)
