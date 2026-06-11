"""Softschema validation for Markdown frontmatter and YAML artifacts.

Two public entry points:

- :func:`validate_artifact` validates a Markdown/YAML document against a
  :class:`~softschema.models.Contract` (reads ``softschema:`` metadata, resolves
  the envelope, runs structural and semantic validation).
- :func:`validate_values` validates an already-extracted values mapping against
  a model, a JSON Schema sidecar, or both.

Lower-level helpers (:func:`validate_structural`, :func:`validate_semantic`) are
public for callers that need a single layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from frontmatter_format import FmFormatError, fmf_read, read_yaml_file
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAMLError

from softschema.canonicalize import apply_enforced_extras
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
) -> StructuralResult:
    """Validate values against a JSON Schema YAML or JSON sidecar.

    With ``strict_extras=True`` (the ``status: enforced`` overlay), object
    schemas that declare ``properties`` but omit ``additionalProperties`` are
    validated as ``additionalProperties: false``; see
    :func:`softschema.canonicalize.apply_enforced_extras`.
    """
    schema = _read_yaml(schema_yaml_path)
    if strict_extras and isinstance(schema, dict):
        schema = apply_enforced_extras(schema)
    validator = Draft202012Validator(schema)
    errors = [
        structural_error_record(
            path=list(error.absolute_path),
            validator=str(error.validator),
            validator_value=error.validator_value,
            value=error.instance,
        )
        for error in validator.iter_errors(values)
    ]
    # Sort for a deterministic, engine-independent order (jsonschema and ajv do
    # not guarantee the same iteration order), so golden output is stable.
    errors.sort(key=lambda record: ([str(part) for part in record["path"]], record["validator"]))
    return StructuralResult(ok=not errors, errors=errors)


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


def validate_artifact(
    doc_path: Path,
    *,
    contract: Contract | None = None,
    contract_id: str | None = None,
    registry: Contracts | None = None,
    metadata_mode: Literal["enforced", "advisory"] = "enforced",
) -> ArtifactValidationResult:
    """Validate an artifact using a complete schema contract."""
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
        return _validate_pure_yaml_artifact(doc_path, contract, warnings)
    return _validate_frontmatter_artifact(doc_path, contract, warnings, metadata_mode)


def _validate_frontmatter_artifact(
    doc_path: Path,
    contract: Contract,
    warnings: list[SchemaWarning],
    metadata_mode: Literal["enforced", "advisory"],
) -> ArtifactValidationResult:
    try:
        _content, frontmatter = _read_frontmatter_doc(doc_path)
    except (FmFormatError, YAMLError, OSError) as exc:
        return _artifact_failure(doc_path, contract, "parse_error", str(exc))
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

    if contract.envelope_key is not None and contract.envelope_key not in frontmatter:
        actual_keys = [str(key) for key in frontmatter if key != "softschema"]
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
                        f"contract {contract.id!r} expects {contract.envelope_key!r}",
                        expected_key=contract.envelope_key,
                        actual_keys=actual_keys,
                    )
                ],
            ),
            semantic=SemanticResult(ok=False, skipped_reason="envelope_mismatch"),
        )

    values = _extract_envelope_values(frontmatter, contract)
    if not isinstance(values, dict):
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
                        "envelope_not_mapping",
                        f"envelope value is {type(values).__name__}, expected mapping",
                    )
                ],
            ),
            semantic=SemanticResult(ok=False, skipped_reason="envelope_not_mapping"),
        )
    return _validate_extracted_values(
        doc_path,
        contract,
        values,
        metadata=metadata,
        warnings=warnings,
    )


def _validate_pure_yaml_artifact(
    doc_path: Path,
    contract: Contract,
    warnings: list[SchemaWarning],
) -> ArtifactValidationResult:
    try:
        raw = _read_yaml(doc_path)
    except (YAMLError, OSError) as exc:
        return _artifact_failure(doc_path, contract, "parse_error", str(exc))
    if not isinstance(raw, dict):
        return _artifact_failure(
            doc_path,
            contract,
            "yaml_not_mapping",
            f"YAML root is {type(raw).__name__}, expected mapping",
        )
    return _validate_extracted_values(doc_path, contract, raw, metadata=None, warnings=warnings)


def _extract_envelope_values(frontmatter: dict[str, Any], contract: Contract) -> Any:
    """Project frontmatter to the values the contract validates.

    With an explicit ``envelope_key`` the named mapping is the payload. Without
    one, the payload is every top-level key except ``softschema``. This is the
    spec's single-envelope rule; there is no value-path resolver.
    """
    if contract.envelope_key is not None:
        return frontmatter[contract.envelope_key]
    return {key: value for key, value in frontmatter.items() if key != "softschema"}


def _metadata_from_frontmatter(
    doc_path: Path,
    frontmatter: dict[str, Any],
    contract: Contract,
    warnings: list[SchemaWarning],
    metadata_mode: Literal["enforced", "advisory"],
) -> SchemaMetadata | ArtifactValidationResult | None:
    try:
        metadata = parse_schema_metadata(frontmatter.get("softschema"))
    except (TypeError, ValidationError) as exc:
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
    schema_path = _resolve_schema_path(contract.schema_path, doc_path)
    if contract.schema_path is not None:
        if schema_path is None:
            structural = StructuralResult(
                ok=False,
                errors=[
                    _error(
                        "schema_sidecar_missing",
                        f"schema sidecar not found: {contract.schema_path}",
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
    """Resolve a sidecar path, searching only the document directory and cwd.

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


def _read_frontmatter_doc(path: Path) -> tuple[str, Any | None]:
    return fmf_read(path)


def _read_yaml(path: Path) -> Any:
    return read_yaml_file(path)


def _error(kind: str, message: str, **details: Any) -> dict[str, Any]:
    return {"kind": kind, "message": message, **details}
