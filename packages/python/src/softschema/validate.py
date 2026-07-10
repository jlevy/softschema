"""softschema validation for Markdown frontmatter and YAML artifacts.

Two public entry points:

- :func:`validate_artifact` validates a Markdown/YAML document against a
  :class:`~softschema.models.Contract` (reads ``softschema:`` metadata, resolves
  the envelope, runs structural and semantic validation).
- :func:`validate_values` validates an already-extracted values mapping against
  a model, a compiled JSON Schema, or both.

Lower-level helpers (:func:`validate_structural`, :func:`validate_semantic`) are
public for callers that need a single layer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Never
from urllib.parse import unquote, urldefrag, urljoin, urlsplit

from frontmatter_format import FmFormatError
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ValidationError
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource
from referencing.jsonschema import DRAFT202012

from softschema.canonicalize import (
    ENFORCEMENT_UNSUPPORTED_MESSAGE,
    EnforcementUnsupportedError,
    apply_enforced_extras,
)
from softschema.errors import (
    SchemaInvalidReason,
    schema_invalid_error,
    structural_error_record,
)
from softschema.models import (
    Contract,
    SchemaMetadata,
    SchemaProfile,
    SchemaStatus,
    SchemaWarning,
    WarningCode,
    parse_schema_metadata,
    validate_contract_id,
    validate_schema_id,
)
from softschema.patterns import first_unsupported_pattern, lower_schema_patterns_for_python
from softschema.registry import Contracts
from softschema.value_domain import (
    DEFAULT_VALIDATION_LIMITS,
    PortableValueError,
    PortableYamlSyntaxError,
    ValidationLimits,
    normalize_portable_value,
    parse_portable_yaml,
)

JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
SchemaResource = bool | dict[str, Any]
SchemaResources = Mapping[str, SchemaResource]
ArtifactParseReason = Literal["frontmatter", "syntax", "root", "value_domain"]
ArtifactInputReason = Literal["not_found", "unreadable", "directory_requires_recursive"]

ARTIFACT_PARSE_MESSAGES: dict[ArtifactParseReason, str] = {
    "frontmatter": "artifact frontmatter delimiters are malformed",
    "syntax": "artifact is not valid YAML",
    "root": "artifact YAML root must be a mapping",
    "value_domain": "artifact contains a non-portable YAML value",
}
ARTIFACT_INPUT_MESSAGES: dict[ArtifactInputReason, str] = {
    "not_found": "artifact path does not exist",
    "unreadable": "artifact path cannot be read",
    "directory_requires_recursive": "artifact directory requires --recursive",
}


class ArtifactFrontmatterError(FmFormatError):
    """A leading frontmatter fence has no closing delimiter."""


class ArtifactRootError(FmFormatError):
    """A readable artifact parsed successfully but its YAML root is not a mapping."""


@dataclass(frozen=True)
class StructuralResult:
    ok: bool
    errors: list[dict[str, Any]] = field(default_factory=list)
    engine: str = "json_schema"
    skipped_reason: str | None = None


@dataclass(frozen=True)
class SemanticResult:
    ok: bool
    errors: list[dict[str, Any]] = field(default_factory=list)
    skipped_reason: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    structural: StructuralResult
    semantic: SemanticResult

    @property
    def ok(self) -> bool:
        return self.structural.ok and self.semantic.ok


@dataclass(frozen=True)
class ArtifactValidationResult:
    """Validation result enriched with contract and document metadata."""

    path: Path
    contract_id: str
    status: SchemaStatus
    profile: SchemaProfile
    structural: StructuralResult
    semantic: SemanticResult
    contract: Contract | None = None
    document_metadata: SchemaMetadata | None = None
    values: dict[str, Any] | None = None
    warnings: list[SchemaWarning] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.structural.ok and self.semantic.ok

    @property
    def warning_codes(self) -> list[str]:
        return [warning.code for warning in self.warnings]


def validate_structural(
    values: Any,
    schema_yaml_path: Path,
    *,
    strict_extras: bool = False,
    resources: SchemaResources | None = None,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
) -> StructuralResult:
    """Validate values against a compiled JSON Schema (YAML or JSON).

    With ``strict_extras=True`` (the ``status: enforced`` overlay), object
    schemas that declare ``properties`` but omit ``additionalProperties`` are
    validated as ``additionalProperties: false``; see
    :func:`softschema.canonicalize.apply_enforced_extras`.

    ``resources`` maps absolute schema URIs to already-loaded mapping or boolean
    schemas. Validation never retrieves a resource from the network or filesystem.
    """
    try:
        schema, root_size_bytes = _read_yaml_resource(schema_yaml_path, limits)
    except PortableValueError as exc:
        return _schema_failure("value_domain", exc.path)
    except (OSError, PortableYamlSyntaxError, UnicodeDecodeError):
        return _schema_failure("syntax", "")
    if not isinstance(schema, dict):
        return _schema_failure("root", "")
    return _validate_structural_schema(
        values,
        schema,
        strict_extras=strict_extras,
        resources=resources,
        limits=limits,
        root_size_bytes=root_size_bytes,
    )


def _validate_structural_schema(
    values: Any,
    schema: dict[str, Any],
    *,
    strict_extras: bool,
    resources: SchemaResources | None,
    limits: ValidationLimits,
    root_size_bytes: int,
) -> StructuralResult:
    supplied_resources = dict(resources or {})
    if 1 + len(supplied_resources) > limits.max_resources:
        return _schema_failure("value_domain", "")
    prepared_resources: dict[str, SchemaResource] = {}
    bundle_size = root_size_bytes
    if bundle_size > limits.max_bundle_bytes:
        return _schema_failure("value_domain", "")
    for uri in sorted(supplied_resources, key=str):
        try:
            normalized, resource_size = normalize_portable_value(
                supplied_resources[uri],
                limits=limits,
            )
        except PortableValueError as exc:
            return _schema_failure("value_domain", exc.path)
        if not isinstance(normalized, bool | dict):
            return _schema_failure("root", "")
        prepared_resources[uri] = normalized
        bundle_size += resource_size
        if bundle_size > limits.max_bundle_bytes:
            return _schema_failure("value_domain", "")
    root_error, legacy_identity = _schema_preflight(
        schema,
        allow_boolean=False,
        legacy_compatible=True,
    )
    if root_error is not None:
        return StructuralResult(ok=False, errors=[root_error])

    for uri in sorted(prepared_resources, key=str):
        try:
            validate_schema_id(uri)
        except ValueError:
            return _schema_failure(
                "identity",
                "",
                detail="invalid_registry_key",
            )
        resource = prepared_resources[uri]
        resource_error, _legacy = _schema_preflight(
            resource,
            allow_boolean=True,
            legacy_compatible=False,
        )
        if resource_error is not None:
            return StructuralResult(ok=False, errors=[resource_error])
        if isinstance(resource, dict) and "$id" in resource and resource["$id"] != uri:
            return _schema_failure(
                "identity",
                "/$id",
                detail="resource_id_mismatch",
            )

    bundle, bundle_error = _build_schema_bundle_index(
        schema,
        prepared_resources,
        legacy_identity=legacy_identity,
    )
    if bundle_error is not None:
        return StructuralResult(ok=False, errors=[bundle_error])
    assert bundle is not None
    if bundle.resource_count > limits.max_resources:
        return _schema_failure("value_domain", "")

    unavailable = _first_unavailable_reference(bundle)
    if unavailable is not None:
        schema_path, reference = unavailable
        return _schema_failure(
            "reference",
            schema_path,
            reference=reference,
        )

    try:
        schema_for_engine = apply_enforced_extras(schema) if strict_extras else dict(schema)
    except EnforcementUnsupportedError as exc:
        return StructuralResult(
            ok=False,
            errors=[
                {
                    "kind": "enforcement_unsupported",
                    "message": ENFORCEMENT_UNSUPPORTED_MESSAGE,
                    "schema_path": exc.schema_path,
                }
            ],
        )
    if legacy_identity:
        schema_for_engine.pop("$id", None)
    lowered_schema, pattern_reversals = lower_schema_patterns_for_python(schema_for_engine)
    assert isinstance(lowered_schema, dict)
    schema_for_engine = lowered_schema
    resources_for_engine: dict[str, SchemaResource] = {}
    for uri in sorted(prepared_resources):
        lowered_resource, resource_reversals = lower_schema_patterns_for_python(
            prepared_resources[uri]
        )
        resources_for_engine[uri] = lowered_resource
        pattern_reversals.update(resource_reversals)

    # Keep the engine boundary offline even if preflight misses an unusual
    # reference shape. Only resources already present in this registry exist.
    registry: Registry[Any] = Registry(retrieve=_deny_schema_retrieval)
    try:
        for uri in sorted(resources_for_engine):
            registry = registry.with_resource(
                uri,
                Resource.from_contents(
                    resources_for_engine[uri],
                    default_specification=DRAFT202012,
                ),
            )
        validator = Draft202012Validator(schema_for_engine, registry=registry)
        engine_errors = list(validator.iter_errors(values))
    except Exception as exc:
        reference = _reference_from_exception(exc)
        if reference is not None:
            located = _find_reference(bundle.references, reference)
            schema_path, original_reference = located or ("", reference)
            return _schema_failure(
                "reference",
                schema_path,
                reference=original_reference,
            )
        return _schema_failure("compile", "")

    errors = []
    for error in engine_errors:
        validator = str(error.validator)
        validator_value = error.validator_value
        if validator == "pattern" and isinstance(validator_value, str):
            validator_value = pattern_reversals.get(validator_value, validator_value)
        errors.append(
            structural_error_record(
                path=list(error.absolute_path),
                validator=validator,
                validator_value=validator_value,
                value=error.instance,
            )
        )
    # Sort for a deterministic, engine-independent order (jsonschema and ajv do
    # not guarantee the same iteration order), so golden output is stable.
    errors.sort(key=lambda record: ([str(part) for part in record["path"]], record["validator"]))
    return StructuralResult(ok=not errors, errors=errors)


def _schema_preflight(
    schema: Any,
    *,
    allow_boolean: bool,
    legacy_compatible: bool,
) -> tuple[dict[str, Any] | None, bool]:
    if isinstance(schema, bool):
        if allow_boolean:
            return None, False
        return schema_invalid_error("root", schema_path=""), False
    if not isinstance(schema, dict):
        return schema_invalid_error("root", schema_path=""), False

    dialect = schema.get("$schema")
    if isinstance(dialect, str) and dialect != JSON_SCHEMA_DRAFT_2020_12:
        return (
            schema_invalid_error(
                "dialect",
                schema_path="/$schema",
                dialect=dialect,
            ),
            False,
        )

    cycle_path = _first_cycle_path(schema)
    if cycle_path is not None:
        return schema_invalid_error("compile", schema_path=cycle_path), False

    invalid_pattern = first_unsupported_pattern(schema)
    if invalid_pattern is not None:
        schema_path, pattern = invalid_pattern
        return (
            schema_invalid_error(
                "pattern",
                schema_path=_json_pointer(list(schema_path)),
                pattern=pattern,
            ),
            False,
        )

    metaschema_path = _metaschema_error_path(schema)
    if metaschema_path is not None:
        return (
            schema_invalid_error(
                "metaschema",
                schema_path=metaschema_path,
            ),
            False,
        )

    if legacy_compatible:
        legacy_identity, identity_error = _legacy_identity(schema)
        if identity_error is not None:
            return identity_error, False
        if legacy_identity:
            return None, True
    root_id = schema.get("$id")
    if isinstance(root_id, str):
        try:
            validate_schema_id(root_id)
        except ValueError:
            return (
                schema_invalid_error(
                    "identity",
                    schema_path="/$id",
                    detail="invalid_root_id",
                ),
                False,
            )
    return None, False


def _first_cycle_path(
    value: Any,
    path: tuple[str | int, ...] = (),
    active: set[int] | None = None,
    complete: set[int] | None = None,
) -> str | None:
    if not isinstance(value, dict | list):
        return None
    active = set() if active is None else active
    complete = set() if complete is None else complete
    identity = id(value)
    if identity in active:
        return _json_pointer(list(path))
    if identity in complete:
        return None

    active.add(identity)
    items = (
        ((str(key), value[key]) for key in sorted(value, key=str))
        if isinstance(value, dict)
        else enumerate(value)
    )
    for key, item in items:
        cycle_path = _first_cycle_path(item, (*path, key), active, complete)
        if cycle_path is not None:
            return cycle_path
    active.remove(identity)
    complete.add(identity)
    return None


def _metaschema_error_path(schema: dict[str, Any]) -> str | None:
    validator = Draft202012Validator(Draft202012Validator.META_SCHEMA)
    errors = sorted(
        validator.iter_errors(schema),
        key=lambda error: (
            _json_pointer(list(error.absolute_path)),
            str(error.validator),
        ),
    )
    if not errors:
        return None
    return _json_pointer(list(errors[0].absolute_path))


def _legacy_identity(
    schema: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    schema_id = schema.get("$id")
    metadata = schema.get("x-softschema")
    contract_id = metadata.get("contract") if isinstance(metadata, dict) else None
    if not isinstance(schema_id, str) or not isinstance(contract_id, str):
        return False, None
    try:
        parse_schema_metadata(schema_id)
        parse_schema_metadata(contract_id)
    except (ValueError, ValidationError):
        return False, None
    if schema_id != contract_id:
        return (
            False,
            schema_invalid_error(
                "profile",
                schema_path="/$id",
                detail="legacy_contract_id_mismatch",
            ),
        )
    return True, None


@dataclass(frozen=True)
class _SchemaReference:
    reference: str
    schema_path: str
    source: SchemaResource
    base_uri: str | None
    origin: str
    legacy_root: bool = False


@dataclass(frozen=True)
class _SchemaBundleIndex:
    resources: dict[str, SchemaResource]
    references: list[_SchemaReference]
    resource_count: int


# Draft 2020-12 keywords whose values contain schemas. Traversal is intentionally
# vocabulary-aware: annotation payloads such as `examples` must never mint resources.
_SINGLE_SCHEMA_KEYWORDS = frozenset(
    {
        "additionalProperties",
        "contains",
        "contentSchema",
        "else",
        "if",
        "items",
        "not",
        "propertyNames",
        "then",
        "unevaluatedItems",
        "unevaluatedProperties",
    }
)
_ARRAY_SCHEMA_KEYWORDS = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
_MAPPING_SCHEMA_KEYWORDS = frozenset(
    {"$defs", "dependentSchemas", "patternProperties", "properties"}
)
_ALL_SCHEMA_KEYWORDS = sorted(
    _SINGLE_SCHEMA_KEYWORDS | _ARRAY_SCHEMA_KEYWORDS | _MAPPING_SCHEMA_KEYWORDS
)


def _schema_children(
    schema: dict[str, Any],
    path: tuple[str | int, ...],
) -> list[tuple[tuple[str | int, ...], SchemaResource]]:
    """Return recognized child schemas in one deterministic document order."""
    children: list[tuple[tuple[str | int, ...], SchemaResource]] = []
    for keyword in _ALL_SCHEMA_KEYWORDS:
        value = schema.get(keyword)
        if keyword in _SINGLE_SCHEMA_KEYWORDS:
            if isinstance(value, bool | dict):
                children.append(((*path, keyword), value))
        elif keyword in _ARRAY_SCHEMA_KEYWORDS:
            if isinstance(value, list):
                children.extend(
                    ((*path, keyword, index), item)
                    for index, item in enumerate(value)
                    if isinstance(item, bool | dict)
                )
        elif isinstance(value, dict):
            children.extend(
                ((*path, keyword, str(name)), value[name])
                for name in sorted(value, key=str)
                if isinstance(value[name], bool | dict)
            )
    return children


_RELATIVE_SCHEMA_PATH_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._~!$&'()*+,;=:@/%-"
)
_RELATIVE_SCHEMA_QUERY_CHARS = _RELATIVE_SCHEMA_PATH_CHARS | frozenset("?")
_URI_UNRESERVED_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._~-"
)


def _has_canonical_relative_schema_id_spelling(schema_id: str) -> bool:
    """Reject aliases a platform URL parser could silently canonicalize."""
    resource_reference, separator, fragment = schema_id.partition("#")
    if separator and fragment:
        return False
    path, _query_separator, query = resource_reference.partition("?")
    if path.startswith("//"):
        authority_end = path.find("/", 2)
        if authority_end < 0:
            return False
        authority = path[2:authority_end]
        try:
            validate_schema_id(f"https://{authority}/")
        except ValueError:
            return False
        path = path[authority_end:]
    if any(char not in _RELATIVE_SCHEMA_PATH_CHARS for char in path):
        return False
    if any(char not in _RELATIVE_SCHEMA_QUERY_CHARS for char in query):
        return False
    index = 0
    while index < len(resource_reference):
        if resource_reference[index] != "%":
            index += 1
            continue
        digits = resource_reference[index + 1 : index + 3]
        if len(digits) != 2 or any(char not in "0123456789ABCDEF" for char in digits):
            return False
        if chr(int(digits, 16)) in _URI_UNRESERVED_CHARS:
            return False
        index += 3
    return True


def _resolve_nested_schema_id(schema_id: str, base_uri: str | None) -> str | None:
    """Resolve a nested `$id` to the canonical resource identity it establishes."""
    if urlsplit(schema_id).scheme:
        resolved = schema_id
    elif base_uri is not None and _has_canonical_relative_schema_id_spelling(schema_id):
        resolved = urljoin(base_uri, schema_id)
    else:
        return None
    resource_uri, fragment = urldefrag(resolved)
    if fragment:
        return None
    try:
        return validate_schema_id(resource_uri)
    except ValueError:
        return None


def _walk_schema_resources(
    schema: SchemaResource,
    *,
    path: tuple[str | int, ...],
    base_uri: str | None,
    source: SchemaResource,
    origin: str,
    resource_index: dict[str, SchemaResource],
    references: list[_SchemaReference],
    resource_root: bool,
    legacy_root: bool,
) -> dict[str, Any] | None:
    if not isinstance(schema, dict):
        return None

    current_base = base_uri
    current_source = source
    if not resource_root and not legacy_root and "$id" in schema:
        raw_id = schema.get("$id")
        resolved_id = (
            _resolve_nested_schema_id(raw_id, current_base) if isinstance(raw_id, str) else None
        )
        if resolved_id is None:
            return schema_invalid_error(
                "identity",
                schema_path=_json_pointer([*path, "$id"]),
                detail="invalid_nested_id",
            )
        if resolved_id in resource_index:
            return schema_invalid_error(
                "identity",
                schema_path=_json_pointer([*path, "$id"]),
                detail="nested_resource_collision",
            )
        resource_index[resolved_id] = schema
        current_base = resolved_id
        current_source = schema

    for key in ("$dynamicRef", "$ref"):
        reference = schema.get(key)
        if isinstance(reference, str):
            references.append(
                _SchemaReference(
                    reference=reference,
                    schema_path=_json_pointer([*path, key]),
                    source=current_source,
                    base_uri=current_base,
                    origin=origin,
                    legacy_root=legacy_root,
                )
            )

    for child_path, child in _schema_children(schema, path):
        error = _walk_schema_resources(
            child,
            path=child_path,
            base_uri=current_base,
            source=current_source,
            origin=origin,
            resource_index=resource_index,
            references=references,
            resource_root=False,
            legacy_root=legacy_root,
        )
        if error is not None:
            return error
    return None


def _build_schema_bundle_index(
    schema: dict[str, Any],
    resources: dict[str, SchemaResource],
    *,
    legacy_identity: bool,
) -> tuple[_SchemaBundleIndex | None, dict[str, Any] | None]:
    """Index top-level and embedded resources before an engine sees the bundle."""
    resource_index = dict(resources)
    root_id = schema.get("$id")
    root_base = None
    if not legacy_identity and isinstance(root_id, str):
        if root_id in resource_index:
            return None, schema_invalid_error(
                "identity",
                schema_path="/$id",
                detail="root_resource_collision",
            )
        resource_index[root_id] = schema
        root_base = root_id

    references: list[_SchemaReference] = []
    error = _walk_schema_resources(
        schema,
        path=(),
        base_uri=root_base,
        source=schema,
        origin="",
        resource_index=resource_index,
        references=references,
        resource_root=True,
        legacy_root=legacy_identity,
    )
    if error is not None:
        return None, error

    for uri in sorted(resources):
        resource = resources[uri]
        error = _walk_schema_resources(
            resource,
            path=(),
            base_uri=uri,
            source=resource,
            origin=uri,
            resource_index=resource_index,
            references=references,
            resource_root=True,
            legacy_root=False,
        )
        if error is not None:
            return None, error

    references.sort(key=lambda item: (item.origin, item.schema_path, item.reference))
    legacy_external = next(
        (item for item in references if item.legacy_root and not item.reference.startswith("#")),
        None,
    )
    if legacy_external is not None:
        return None, schema_invalid_error(
            "profile",
            schema_path=legacy_external.schema_path,
            detail="legacy_external_reference",
        )
    resource_count = len(resource_index) + (root_base is None)
    return _SchemaBundleIndex(resource_index, references, resource_count), None


def _first_unavailable_reference(
    bundle: _SchemaBundleIndex,
) -> tuple[str, str] | None:
    for reference in bundle.references:
        if not _reference_is_available(reference, bundle.resources):
            return reference.schema_path, reference.reference
    return None


def _reference_is_available(
    candidate: _SchemaReference,
    resources: SchemaResources,
) -> bool:
    reference = candidate.reference
    if reference.startswith("#"):
        return _fragment_exists(candidate.source, reference[1:])
    resource_uri, fragment = urldefrag(reference)
    if resource_uri == "":
        return _fragment_exists(candidate.source, fragment)
    resolved_uri = _resolve_reference_uri(resource_uri, candidate.base_uri)
    if resolved_uri is None:
        return False
    target = resources.get(resolved_uri)
    if target is None:
        return False
    return _fragment_exists(target, fragment)


def _resolve_reference_uri(reference: str, base_uri: str | None) -> str | None:
    if urlsplit(reference).scheme:
        return reference
    if base_uri is None:
        return None
    resolved = urljoin(base_uri, reference)
    return resolved if urlsplit(resolved).scheme else None


def _fragment_exists(resource: SchemaResource, fragment: str) -> bool:
    fragment = unquote(fragment)
    if fragment == "":
        return True
    if fragment.startswith("/"):
        current: Any = resource
        for encoded_token in fragment[1:].split("/"):
            token = encoded_token.replace("~1", "/").replace("~0", "~")
            if isinstance(current, dict) and token in current:
                current = current[token]
            elif isinstance(current, list) and token.isdecimal() and int(token) < len(current):
                current = current[int(token)]
            else:
                return False
        return True
    return _has_anchor(resource, fragment)


def _has_anchor(value: Any, anchor: str, *, resource_root: bool = True) -> bool:
    if not isinstance(value, dict):
        return False
    if not resource_root and "$id" in value:
        return False
    if value.get("$anchor") == anchor or value.get("$dynamicAnchor") == anchor:
        return True
    return any(
        _has_anchor(child, anchor, resource_root=False)
        for _path, child in _schema_children(value, ())
    )


def _reference_from_exception(exc: Exception) -> str | None:
    current: BaseException | None = exc
    while current is not None:
        reference = getattr(current, "ref", None)
        if isinstance(reference, str):
            return reference
        if current.__class__.__module__.startswith("referencing"):
            return str(current.args[0]) if current.args else ""
        current = current.__cause__
    return None


def _deny_schema_retrieval(uri: str) -> Never:
    """Reject every engine retrieval request; resources must already be loaded."""
    raise NoSuchResource(ref=uri)


def _find_reference(
    candidates: list[_SchemaReference],
    reference: str,
) -> tuple[str, str] | None:
    for candidate in candidates:
        resource_uri, _fragment = urldefrag(candidate.reference)
        resolved = _resolve_reference_uri(resource_uri, candidate.base_uri)
        if candidate.reference == reference or resolved == urldefrag(reference)[0]:
            return candidate.schema_path, candidate.reference
    return None


def _json_pointer(path: list[str | int]) -> str:
    return "".join(f"/{str(part).replace('~', '~0').replace('/', '~1')}" for part in path)


def _schema_failure(
    reason: SchemaInvalidReason,
    schema_path: str,
    **details: Any,
) -> StructuralResult:
    return StructuralResult(
        ok=False,
        errors=[schema_invalid_error(reason, schema_path=schema_path, **details)],
    )


def validate_semantic(values: Any, model_cls: type[BaseModel]) -> SemanticResult:
    """Validate values by calling ``model_cls.model_validate``."""
    try:
        model_cls.model_validate(values)
    except ValidationError as exc:
        return SemanticResult(ok=False, errors=[dict(error) for error in exc.errors()])
    return SemanticResult(ok=True)


def validate_values(
    values: Any,
    *,
    model: type[BaseModel] | None = None,
    schema: Path | None = None,
    resources: SchemaResources | None = None,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
) -> ValidationResult:
    """Validate a pre-extracted values mapping against a model, a schema, or both.

    Returns a ``ValidationResult`` with separate ``structural`` and ``semantic``
    fields. Engines that were not requested are reported as ok (with no errors)
    so callers can read either field without checking which one ran.

    Use this when values come from somewhere other than a Markdown frontmatter
    document (a body-form runtime, a structured-output adapter, a hand-written
    fixture). For Markdown documents use ``validate_artifact`` instead.

    ``resources`` has the same already-loaded, no-retrieval semantics as
    :func:`validate_structural`.
    """
    if model is None and schema is None:
        raise ValueError("validate_values() requires at least one of model= or schema=")
    structural = (
        validate_structural(values, schema, resources=resources, limits=limits)
        if schema
        else StructuralResult(ok=True)
    )
    semantic = validate_semantic(values, model) if model else SemanticResult(ok=True)
    return ValidationResult(structural=structural, semantic=semantic)


_UNREAD: Any = object()


def validate_artifact(
    doc_path: Path,
    *,
    contract: Contract | None = None,
    contract_id: str | None = None,
    registry: Contracts | None = None,
    metadata_mode: Literal["enforced", "advisory"] = "enforced",
    frontmatter: Any = _UNREAD,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
) -> ArtifactValidationResult:
    """Validate an artifact using a complete schema contract.

    ``frontmatter`` is an optional already-parsed frontmatter mapping (as
    returned by ``frontmatter_format.fmf_read``); when supplied for a
    frontmatter-md contract the document is not re-read. A caller that has
    already parsed the document (the CLI does, to infer the binding) passes it
    to avoid a second read. ``None`` is a valid value (no frontmatter); the
    sentinel ``_UNREAD`` means "read the file".
    """
    if contract_id is not None:
        validate_contract_id(contract_id)
    if contract is not None:
        validate_contract_id(contract.id)
    if contract is None and contract_id is not None and registry is not None:
        contract = registry.resolve(contract_id)
    if contract is None:
        resolved_contract_id = contract_id or "<unknown>"
        return ArtifactValidationResult(
            path=doc_path,
            contract_id=resolved_contract_id,
            status=SchemaStatus.soft,
            profile=SchemaProfile.frontmatter_md,
            contract=None,
            structural=StructuralResult(
                ok=False,
                errors=[
                    _error(
                        "contract_unknown",
                        f"no softschema contract registered for {resolved_contract_id!r}",
                        contract_id=resolved_contract_id,
                    )
                ],
            ),
            semantic=SemanticResult(ok=False, skipped_reason="contract_unknown"),
        )

    warnings: list[SchemaWarning] = []
    if contract.profile == SchemaProfile.pure_yaml:
        return _validate_pure_yaml_artifact(
            doc_path,
            contract,
            warnings,
            metadata_mode,
            limits,
            raw=frontmatter,
        )
    return _validate_frontmatter_artifact(
        doc_path,
        contract,
        warnings,
        metadata_mode,
        frontmatter,
        limits,
    )


def _validate_frontmatter_artifact(
    doc_path: Path,
    contract: Contract,
    warnings: list[SchemaWarning],
    metadata_mode: Literal["enforced", "advisory"],
    frontmatter: Any = _UNREAD,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
) -> ArtifactValidationResult:
    if frontmatter is _UNREAD:
        try:
            _content, frontmatter = _read_frontmatter_doc(doc_path, limits)
        except (
            ArtifactFrontmatterError,
            ArtifactRootError,
            PortableValueError,
            PortableYamlSyntaxError,
            UnicodeDecodeError,
            OSError,
        ) as exc:
            return _artifact_read_failure(doc_path, contract, exc)
    elif frontmatter is not None:
        try:
            frontmatter, _size = normalize_portable_value(frontmatter, limits=limits)
        except PortableValueError as exc:
            return _artifact_value_domain_failure(doc_path, contract, exc)
    if frontmatter is None:
        return _artifact_failure(
            doc_path, contract, "no_frontmatter", f"no frontmatter in {doc_path}"
        )
    if not isinstance(frontmatter, dict):
        return _artifact_failure_from_record(
            doc_path,
            contract,
            artifact_parse_error_record(doc_path, "root"),
        )

    metadata_result = _metadata_from_frontmatter(
        doc_path, frontmatter, contract, warnings, metadata_mode
    )
    if isinstance(metadata_result, ArtifactValidationResult):
        return metadata_result
    metadata = metadata_result

    # Envelope precedence (host over document): a registry/caller envelope_key,
    # then the document's own softschema.envelope, then single-key inference.
    declared_envelope = contract.envelope_key or (metadata.envelope if metadata else None)
    if declared_envelope is not None:
        if declared_envelope not in frontmatter:
            return _envelope_mismatch_result(
                doc_path, contract, metadata, warnings, frontmatter, declared_envelope
            )
        values = frontmatter[declared_envelope]
    else:
        # The spec's envelope rules: exactly one non-softschema top-level key is
        # the envelope by convention; zero or several candidates are rejected.
        try:
            envelope_key = infer_envelope_key(frontmatter)
        except EnvelopeAmbiguityError as exc:
            return _artifact_failure(
                doc_path,
                contract,
                "envelope_ambiguous",
                str(exc),
                metadata=metadata,
                warnings=warnings,
            )
        if envelope_key is None:
            return _artifact_failure(
                doc_path,
                contract,
                "envelope_missing",
                "document has no payload key beside softschema",
                metadata=metadata,
                warnings=warnings,
            )
        values = frontmatter[envelope_key]

    if not isinstance(values, dict):
        return _artifact_failure(
            doc_path,
            contract,
            "envelope_not_mapping",
            f"envelope value is {type(values).__name__}, expected mapping",
            metadata=metadata,
            warnings=warnings,
        )
    return _validate_extracted_values(
        doc_path,
        contract,
        values,
        metadata=metadata,
        warnings=warnings,
        limits=limits,
    )


def _envelope_mismatch_result(
    doc_path: Path,
    contract: Contract,
    metadata: SchemaMetadata | None,
    warnings: list[SchemaWarning],
    root: dict[str, Any],
    expected_key: str,
) -> ArtifactValidationResult:
    actual_keys = [str(key) for key in root if key != "softschema"]
    return ArtifactValidationResult(
        path=doc_path,
        contract_id=contract.id,
        status=contract.status,
        profile=contract.profile,
        contract=contract,
        document_metadata=metadata,
        warnings=warnings,
        structural=StructuralResult(
            ok=False,
            errors=[
                _error(
                    "envelope_mismatch",
                    f"contract {contract.id!r} expects {expected_key!r}",
                    expected_key=expected_key,
                    actual_keys=actual_keys,
                )
            ],
        ),
        semantic=SemanticResult(ok=False, skipped_reason="envelope_mismatch"),
    )


def _validate_pure_yaml_artifact(
    doc_path: Path,
    contract: Contract,
    warnings: list[SchemaWarning],
    metadata_mode: Literal["enforced", "advisory"],
    limits: ValidationLimits,
    *,
    raw: Any = _UNREAD,
) -> ArtifactValidationResult:
    """Validate a pure-yaml artifact.

    The document root follows the same metadata rules as frontmatter: an
    optional ``softschema:`` block is recognized (and checked) rather than
    validated as payload data.
    The envelope differs by design: with an explicit ``envelope_key`` the named
    key nests the payload; otherwise the remaining root (minus the metadata
    block) IS the payload, because a pure-yaml file is "the whole document is
    the structured payload" (e.g. a companion data file), so single-key inference and
    ambiguity rejection do not apply.
    """
    if raw is _UNREAD:
        try:
            raw = read_yaml_artifact(doc_path, limits)
        except (
            ArtifactRootError,
            PortableValueError,
            PortableYamlSyntaxError,
            UnicodeDecodeError,
            OSError,
        ) as exc:
            return _artifact_read_failure(doc_path, contract, exc)
    else:
        try:
            raw, _size = normalize_portable_value(raw, limits=limits)
        except PortableValueError as exc:
            return _artifact_read_failure(doc_path, contract, exc)
    if not isinstance(raw, dict):
        return _artifact_failure_from_record(
            doc_path,
            contract,
            artifact_parse_error_record(doc_path, "root"),
        )

    metadata_result = _metadata_from_frontmatter(doc_path, raw, contract, warnings, metadata_mode)
    if isinstance(metadata_result, ArtifactValidationResult):
        return metadata_result
    metadata = metadata_result

    declared_envelope = contract.envelope_key or (metadata.envelope if metadata else None)
    if declared_envelope is not None:
        if declared_envelope not in raw:
            return _envelope_mismatch_result(
                doc_path, contract, metadata, warnings, raw, declared_envelope
            )
        values = raw[declared_envelope]
    else:
        values = {key: value for key, value in raw.items() if key != "softschema"}
    if not isinstance(values, dict):
        return _artifact_failure(
            doc_path,
            contract,
            "envelope_not_mapping",
            f"envelope value is {type(values).__name__}, expected mapping",
            metadata=metadata,
            warnings=warnings,
        )
    return _validate_extracted_values(
        doc_path,
        contract,
        values,
        metadata=metadata,
        warnings=warnings,
        limits=limits,
    )


class EnvelopeAmbiguityError(ValueError):
    """Multiple top-level payload candidates; the envelope must be designated."""

    def __init__(self, candidates: list[str]) -> None:
        self.candidates = candidates
        super().__init__(
            "multiple top-level frontmatter keys; designate the softschema payload "
            f"(candidates: {', '.join(candidates)})"
        )


def infer_envelope_key(frontmatter: dict[str, Any]) -> str | None:
    """Infer the spec's single envelope key from a frontmatter mapping.

    Returns the single non-``softschema`` top-level key, ``None`` when there is
    no candidate, and raises :class:`EnvelopeAmbiguityError` when several keys
    are present (the caller must designate the envelope explicitly).
    """
    candidates = [str(key) for key in frontmatter if key != "softschema"]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    raise EnvelopeAmbiguityError(candidates)


def _metadata_from_frontmatter(
    doc_path: Path,
    frontmatter: dict[str, Any],
    contract: Contract,
    warnings: list[SchemaWarning],
    metadata_mode: Literal["enforced", "advisory"],
) -> SchemaMetadata | ArtifactValidationResult | None:
    try:
        metadata = parse_schema_metadata(frontmatter.get("softschema"))
    except (ValueError, ValidationError) as exc:
        return _artifact_failure(
            doc_path,
            contract,
            "document_softschema_invalid",
            str(exc),
            warnings=warnings,
        )
    if metadata is None:
        return None
    if metadata.contract_id != contract.id:
        message = f"document declares {metadata.contract_id!r}; contract uses {contract.id!r}"
        if metadata_mode == "advisory":
            warnings.append(
                SchemaWarning(code=WarningCode.DOCUMENT_CONTRACT_MISMATCH, message=message)
            )
        else:
            return _artifact_failure(
                doc_path,
                contract,
                "document_contract_mismatch",
                message,
                metadata=metadata,
                warnings=warnings,
            )
    if metadata.status is not None and metadata.status != contract.status:
        warnings.append(
            SchemaWarning(
                code=WarningCode.DOCUMENT_STATUS_MISMATCH,
                message=(
                    f"document declares status {metadata.status.value!r}; contract uses "
                    f"{contract.status.value!r}"
                ),
            )
        )
    return metadata


def _validate_extracted_values(
    doc_path: Path,
    contract: Contract,
    values: dict[str, Any],
    *,
    metadata: SchemaMetadata | None,
    warnings: list[SchemaWarning],
    limits: ValidationLimits,
) -> ArtifactValidationResult:
    # Schema precedence (host over document): a caller/registry schema_path,
    # then the document's own softschema.schema binding, then none.
    metadata_schema = metadata.schema_ref if metadata is not None else None
    if contract.schema_path is not None:
        schema_path = _resolve_schema_path(contract.schema_path, doc_path)
        if schema_path is None:
            structural = StructuralResult(
                ok=False,
                errors=[
                    _error(
                        "schema_missing",
                        f"compiled schema not found: {contract.schema_path}",
                        path=str(contract.schema_path),
                    )
                ],
            )
        else:
            structural = validate_structural(
                values,
                schema_path,
                strict_extras=contract.status == SchemaStatus.enforced,
                limits=limits,
            )
    elif metadata_schema is not None:
        bound_path, bind_error = _resolve_metadata_schema(metadata_schema, doc_path)
        if bound_path is None:
            structural = StructuralResult(
                ok=False,
                errors=[_error("schema_missing", bind_error or "", path=metadata_schema)],
            )
        else:
            structural = validate_structural(
                values,
                bound_path,
                strict_extras=contract.status == SchemaStatus.enforced,
                limits=limits,
            )
    elif contract.model is not None:
        structural = StructuralResult(ok=True, skipped_reason="inferred_via_model")
    else:
        structural = StructuralResult(ok=True, skipped_reason="no_schema")

    semantic = (
        validate_semantic(values, contract.model)
        if contract.model is not None
        else SemanticResult(ok=True, skipped_reason="no_semantic_model")
    )
    return ArtifactValidationResult(
        path=doc_path,
        contract_id=contract.id,
        status=contract.status,
        profile=contract.profile,
        contract=contract,
        document_metadata=metadata,
        values=values,
        warnings=warnings,
        structural=structural,
        semantic=semantic,
    )


def _resolve_schema_path(path: Path | None, doc_path: Path) -> Path | None:
    """Resolve a compiled schema path, searching only the document directory and cwd.

    The search is intentionally bounded to two locations so resolution is
    predictable and cannot silently bind to an unrelated ``*.schema.yaml`` in a
    parent directory.
    """
    if path is None:
        return None
    if path.exists():
        return path
    if path.is_absolute():
        return None
    for base in (doc_path.parent, Path.cwd()):
        candidate = base / path
        if candidate.exists():
            return candidate
    return None


def _resolve_metadata_schema(schema_ref: str, doc_path: Path) -> tuple[Path | None, str | None]:
    """Resolve a document-declared ``softschema.schema`` value, strictly bounded.

    Stricter than :func:`_resolve_schema_path` because the value comes from the
    document, not the caller: it must be a relative path, resolves from the
    document's directory, and the normalized result must stay inside the
    document directory or the working directory (so a document cannot bind an
    arbitrary file). Returns ``(path, None)`` on success or ``(None, message)``
    on rejection; every rejection reports as ``schema_missing``.
    """
    ref = Path(schema_ref)
    if ref.is_absolute():
        return None, f"softschema.schema must be a relative path: {schema_ref}"
    resolved = (doc_path.parent / ref).resolve()
    doc_dir = doc_path.parent.resolve()
    cwd = Path.cwd().resolve()
    if not (resolved.is_relative_to(doc_dir) or resolved.is_relative_to(cwd)):
        return None, (
            "softschema.schema escapes the document directory and the working "
            f"directory: {schema_ref}"
        )
    if not resolved.is_file():
        return None, f"compiled schema not found: {schema_ref}"
    return resolved, None


def _artifact_failure(
    doc_path: Path,
    contract: Contract,
    kind: str,
    message: str,
    *,
    metadata: SchemaMetadata | None = None,
    warnings: list[SchemaWarning] | None = None,
    details: Mapping[str, Any] | None = None,
) -> ArtifactValidationResult:
    return ArtifactValidationResult(
        path=doc_path,
        contract_id=contract.id,
        status=contract.status,
        profile=contract.profile,
        contract=contract,
        document_metadata=metadata,
        warnings=warnings or [],
        structural=StructuralResult(ok=False, errors=[_error(kind, message, **(details or {}))]),
        semantic=SemanticResult(ok=False, skipped_reason=kind),
    )


def _artifact_value_domain_failure(
    doc_path: Path,
    contract: Contract,
    error: PortableValueError,
) -> ArtifactValidationResult:
    return _artifact_failure_from_record(
        doc_path,
        contract,
        artifact_parse_error_record(doc_path, "value_domain", path=error.path),
    )


def artifact_parse_error_record(
    source: Path | str,
    reason: ArtifactParseReason,
    *,
    path: str | None = None,
    line: int | None = None,
    column: int | None = None,
    include_location: bool = False,
) -> dict[str, Any]:
    """Build a stable discriminated record for a readable artifact parse failure."""
    record: dict[str, Any] = {
        "kind": "parse_error",
        "reason": reason,
        "message": ARTIFACT_PARSE_MESSAGES[reason],
        "source": str(source),
    }
    if reason == "value_domain":
        record["path"] = path or ""
    elif path is not None:
        record["path"] = path
    if include_location:
        if line is not None:
            record["line"] = line
        if column is not None:
            record["column"] = column
    return record


def artifact_input_error_record(
    source: Path | str,
    reason: ArtifactInputReason,
) -> dict[str, Any]:
    """Build a stable discriminated record for an artifact access failure."""
    return {
        "kind": "input_error",
        "reason": reason,
        "message": ARTIFACT_INPUT_MESSAGES[reason],
        "source": str(source),
    }


def artifact_error_record(
    source: Path | str,
    error: BaseException,
    *,
    include_location: bool = False,
) -> dict[str, Any] | None:
    """Normalize a parser/filesystem exception without exposing platform prose."""
    if isinstance(error, PortableValueError):
        return artifact_parse_error_record(
            source,
            "value_domain",
            path=error.path,
            line=error.line,
            column=error.column,
            include_location=include_location,
        )
    if isinstance(error, ArtifactFrontmatterError):
        return artifact_parse_error_record(source, "frontmatter")
    if isinstance(error, ArtifactRootError):
        return artifact_parse_error_record(source, "root")
    if isinstance(error, PortableYamlSyntaxError):
        return artifact_parse_error_record(
            source,
            "syntax",
            line=error.line,
            column=error.column,
            include_location=include_location,
        )
    if isinstance(error, UnicodeDecodeError):
        return artifact_parse_error_record(source, "syntax")
    if isinstance(error, IsADirectoryError):
        return artifact_input_error_record(source, "directory_requires_recursive")
    if isinstance(error, (FileNotFoundError, NotADirectoryError)):
        return artifact_input_error_record(source, "not_found")
    if isinstance(error, OSError):
        return artifact_input_error_record(source, "unreadable")
    return None


def _artifact_read_failure(
    doc_path: Path,
    contract: Contract,
    error: BaseException,
) -> ArtifactValidationResult:
    record = artifact_error_record(doc_path, error)
    if record is None:
        raise error
    return _artifact_failure_from_record(doc_path, contract, record)


def _artifact_failure_from_record(
    doc_path: Path,
    contract: Contract,
    record: Mapping[str, Any],
) -> ArtifactValidationResult:
    return _artifact_failure(
        doc_path,
        contract,
        str(record["kind"]),
        str(record["message"]),
        details={key: value for key, value in record.items() if key not in {"kind", "message"}},
    )


def _read_frontmatter_doc(
    path: Path,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
) -> tuple[str, Any | None]:
    if path.is_dir():
        raise IsADirectoryError(path)
    encoded = path.read_bytes()
    if len(encoded) > limits.max_resource_bytes:
        raise PortableValueError("maximum resource size exceeded")
    text = encoded.decode("utf-8-sig")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text, None
    end = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"), -1)
    if end < 0:
        raise ArtifactFrontmatterError(
            f"Delimiter `---` for end of frontmatter not found: `{path}`"
        )
    body = "".join(lines[end + 1 :])
    if end == 1:
        return body, None
    frontmatter = parse_portable_yaml(
        "".join(lines[1:end]),
        limits=limits,
        encoded_size=len(encoded),
        line_offset=1,
    )
    if not isinstance(frontmatter, dict):
        raise ArtifactRootError(
            "Expected YAML metadata to be a dict, got "
            f"<class '{type(frontmatter).__name__}'>: `{path}`"
        )
    return body, frontmatter


def read_frontmatter(
    path: Path,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
) -> tuple[str, Any | None]:
    """Read bounded portable frontmatter with the legacy ``fmf_read`` return shape."""
    return _read_frontmatter_doc(path, limits)


def _read_yaml(
    path: Path,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
) -> Any:
    value, _size = _read_yaml_resource(path, limits)
    return value


def read_yaml_artifact(
    path: Path,
    limits: ValidationLimits = DEFAULT_VALIDATION_LIMITS,
) -> dict[str, Any]:
    """Read one bounded pure-YAML artifact and require a mapping root."""
    value = _read_yaml(path, limits)
    if not isinstance(value, dict):
        raise ArtifactRootError(f"YAML root is {type(value).__name__}, expected mapping")
    return value


def _read_yaml_resource(path: Path, limits: ValidationLimits) -> tuple[Any, int]:
    if path.is_dir():
        raise IsADirectoryError(path)
    encoded = path.read_bytes()
    value = parse_portable_yaml(
        encoded.decode("utf-8-sig"),
        limits=limits,
        encoded_size=len(encoded),
    )
    return value, len(encoded)


def _error(kind: str, message: str, **details: Any) -> dict[str, Any]:
    return {"kind": kind, "message": message, **details}
