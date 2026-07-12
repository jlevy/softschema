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

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator, SchemaError
from pydantic import BaseModel, ValidationError
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012

from softschema._portable import PortableInputError, parse_yaml, read_utf8
from softschema.canonicalize import EnforcementUnsupportedError, apply_enforced_extras
from softschema.errors import structural_error_record
from softschema.models import (
    Contract,
    SchemaMetadata,
    SchemaProfile,
    SchemaStatus,
    SchemaWarning,
    WarningCode,
    parse_schema_metadata,
)
from softschema.registry import Contracts


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
    outcome: Literal["valid", "invalid", "input_error"] = field(init=False)

    def __post_init__(self) -> None:
        input_codes = {"artifact_unreadable", "artifact_invalid_utf8", "artifact_too_large"}
        first_kind = self.structural.errors[0].get("kind") if self.structural.errors else None
        outcome = "valid" if self.ok else "input_error" if first_kind in input_codes else "invalid"
        object.__setattr__(self, "outcome", outcome)

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
    resources: Mapping[str, dict[str, Any]] | None = None,
) -> StructuralResult:
    """Validate values against a compiled JSON Schema (YAML or JSON).

    With ``strict_extras=True`` (the ``status: enforced`` overlay), object
    schemas that declare ``properties`` but omit ``additionalProperties`` are
    validated as ``additionalProperties: false``; see
    :func:`softschema.canonicalize.apply_enforced_extras`.
    """
    try:
        schema = _read_yaml(schema_yaml_path)
        if not isinstance(schema, dict):
            return _schema_invalid("syntax", "compiled schema root must be a mapping")
        _check_patterns(schema)
        Draft202012Validator.check_schema(schema)
        _check_schema_identities(schema, resources or {})
        if strict_extras:
            schema = apply_enforced_extras(schema)
        registry: Registry[Any] = Registry()
        for key, resource_schema in (resources or {}).items():
            resource_id = str(resource_schema.get("$id", key))
            registry = registry.with_resource(
                resource_id,
                Resource.from_contents(resource_schema, default_specification=DRAFT202012),
            )
        registry = registry.crawl()
        validator = Draft202012Validator(schema, registry=registry)
        errors = [
            structural_error_record(
                path=list(error.absolute_path),
                validator=str(error.validator),
                validator_value=error.validator_value,
                value=error.instance,
            )
            for error in validator.iter_errors(values)
        ]
    except PortableInputError as exc:
        return _schema_invalid("syntax", str(exc))
    except SchemaError as exc:
        return _schema_invalid("dialect", exc.message)
    except Unresolvable as exc:
        return _schema_invalid("reference", str(exc))
    except re.error as exc:
        return _schema_invalid("pattern", str(exc))
    except EnforcementUnsupportedError as exc:
        return StructuralResult(
            ok=False,
            errors=[{"kind": "enforcement_unsupported", "message": str(exc)}],
        )
    except Exception as exc:
        return _schema_invalid(_schema_failure_reason(exc), str(exc))
    # Sort for a deterministic, engine-independent order (jsonschema and ajv do
    # not guarantee the same iteration order), so golden output is stable.
    errors.sort(key=lambda record: ([str(part) for part in record["path"]], record["validator"]))
    return StructuralResult(ok=not errors, errors=errors)


_SCHEMA_MAPS = frozenset(
    {"$defs", "definitions", "properties", "patternProperties", "dependentSchemas"}
)
_SCHEMA_LISTS = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
_SCHEMA_SINGLES = frozenset(
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
_MAX_PATTERN_LENGTH = 1_024
_UNSUPPORTED_PATTERN_PARTS = ("(?<", "(?P", "\\A", "\\Z", "\\z", "\\p", "\\P")


def _iter_schemas(root: dict[str, Any]) -> Iterator[dict[str, Any]]:
    stack = [root]
    while stack:
        schema = stack.pop()
        yield schema
        for key, value in schema.items():
            if key in _SCHEMA_MAPS and isinstance(value, dict):
                stack.extend(item for item in value.values() if isinstance(item, dict))
            elif key in _SCHEMA_LISTS and isinstance(value, list):
                stack.extend(item for item in value if isinstance(item, dict))
            elif key in _SCHEMA_SINGLES and isinstance(value, dict):
                stack.append(value)


def _check_patterns(schema: dict[str, Any]) -> None:
    def check(pattern: Any) -> None:
        if not isinstance(pattern, str) or len(pattern) > _MAX_PATTERN_LENGTH:
            raise ValueError("pattern must be a string of at most 1024 characters")
        if any(part in pattern for part in _UNSUPPORTED_PATTERN_PARTS) or re.search(
            r"\\[1-9]|\(\?[aiLmsux-]", pattern
        ):
            raise ValueError("pattern uses syntax outside the portable subset")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"pattern is invalid: {exc}") from exc

    for node in _iter_schemas(schema):
        pattern = node.get("pattern")
        if pattern is not None:
            check(pattern)
        pattern_properties = node.get("patternProperties")
        if isinstance(pattern_properties, dict):
            for property_pattern in pattern_properties:
                check(property_pattern)


def _check_schema_identities(
    schema: dict[str, Any], resources: Mapping[str, dict[str, Any]]
) -> None:
    seen: set[str] = set()
    for document in (schema, *resources.values()):
        for node in _iter_schemas(document):
            resource_id = node.get("$id")
            if not isinstance(resource_id, str):
                continue
            if resource_id in seen:
                raise ValueError(f"duplicate schema resource identity: {resource_id}")
            seen.add(resource_id)


def _schema_failure_reason(error: Exception) -> str:
    message = str(error).lower()
    if "reference" in message or "unresolvable" in message:
        return "reference"
    if "pattern" in message:
        return "pattern"
    if "duplicate schema resource" in message:
        return "resource_identity"
    return "compilation"


def _schema_invalid(reason: str, message: str) -> StructuralResult:
    return StructuralResult(
        ok=False,
        errors=[{"kind": "schema_invalid", "reason": reason, "message": message}],
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
) -> ValidationResult:
    """Validate a pre-extracted values mapping against a model, a schema, or both.

    Returns a ``ValidationResult`` with separate ``structural`` and ``semantic``
    fields. Engines that were not requested are reported as ok (with no errors)
    so callers can read either field without checking which one ran.

    Use this when values come from somewhere other than a Markdown frontmatter
    document (a body-form runtime, a structured-output adapter, a hand-written
    fixture). For Markdown documents use ``validate_artifact`` instead.
    """
    if model is None and schema is None:
        raise ValueError("validate_values() requires at least one of model= or schema=")
    structural = validate_structural(values, schema) if schema else StructuralResult(ok=True)
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
) -> ArtifactValidationResult:
    """Validate an artifact using a complete schema contract.

    ``frontmatter`` is an optional already-parsed frontmatter mapping. When supplied for
    a frontmatter-md contract the document is not re-read. The CLI passes its binding
    parse to keep validation single-read. ``None`` is a valid value (no frontmatter);
    the sentinel ``_UNREAD`` means "read the file".
    """
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
        return _validate_pure_yaml_artifact(doc_path, contract, warnings, metadata_mode)
    return _validate_frontmatter_artifact(doc_path, contract, warnings, metadata_mode, frontmatter)


def _validate_frontmatter_artifact(
    doc_path: Path,
    contract: Contract,
    warnings: list[SchemaWarning],
    metadata_mode: Literal["enforced", "advisory"],
    frontmatter: Any = _UNREAD,
) -> ArtifactValidationResult:
    if frontmatter is _UNREAD:
        try:
            _content, frontmatter = read_frontmatter_doc(doc_path)
        except OSError as exc:
            return _artifact_failure(doc_path, contract, "artifact_unreadable", str(exc))
        except PortableInputError as exc:
            kind = _portable_error_kind(exc)
            return _artifact_failure(doc_path, contract, kind, str(exc))
    if frontmatter is None:
        return _artifact_failure(
            doc_path, contract, "no_frontmatter", f"no frontmatter in {doc_path}"
        )
    if not isinstance(frontmatter, dict):
        return _artifact_failure(
            doc_path,
            contract,
            "frontmatter_not_mapping",
            "frontmatter is not a mapping",
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
    try:
        raw = _read_yaml(doc_path)
    except OSError as exc:
        return _artifact_failure(doc_path, contract, "artifact_unreadable", str(exc))
    except PortableInputError as exc:
        return _artifact_failure(doc_path, contract, _portable_error_kind(exc), str(exc))
    if not isinstance(raw, dict):
        return _artifact_failure(
            doc_path,
            contract,
            "yaml_not_mapping",
            f"YAML root is {type(raw).__name__}, expected mapping",
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
        doc_path, contract, values, metadata=metadata, warnings=warnings
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
) -> ArtifactValidationResult:
    return ArtifactValidationResult(
        path=doc_path,
        contract_id=contract.id,
        status=contract.status,
        profile=contract.profile,
        contract=contract,
        document_metadata=metadata,
        warnings=warnings or [],
        structural=StructuralResult(ok=False, errors=[_error(kind, message)]),
        semantic=SemanticResult(ok=False, skipped_reason=kind),
    )


def read_frontmatter_doc(path: Path) -> tuple[str, Any | None]:
    text = read_utf8(path)
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return text, None
    end = next((index for index, line in enumerate(lines[1:], 1) if line.rstrip() == "---"), -1)
    if end < 0:
        raise PortableInputError(
            "yaml_parse_error", f"Delimiter `---` for end of frontmatter not found: `{path}`"
        )
    if end == 1:
        return "\n".join(lines[2:]), None
    raw = "\n".join(lines[1:end])
    value = parse_yaml(raw)
    if not isinstance(value, dict):
        raise PortableInputError(
            "yaml_parse_error",
            f"Expected YAML metadata to be a dict, got {type(value).__name__}: `{path}`",
        )
    return "\n".join(lines[end + 1 :]), value


def _read_yaml(path: Path) -> Any:
    return parse_yaml(read_utf8(path))


def _portable_error_kind(error: Exception) -> str:
    if not isinstance(error, PortableInputError):
        return "yaml_parse_error"
    if error.code == "invalid_utf8":
        return "artifact_invalid_utf8"
    if error.code == "input_too_large":
        return "artifact_too_large"
    return error.code


def _error(kind: str, message: str, **details: Any) -> dict[str, Any]:
    return {"kind": kind, "message": message, **details}
