"""Softschema validation for Markdown frontmatter and YAML artifacts."""

from __future__ import annotations

import gzip
import tempfile
from collections.abc import Callable
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
from frontmatter_format import FmFormatError, fmf_read, read_yaml_file
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaError
from pydantic import BaseModel, ValidationError

from softschema.models import (
    SoftschemaBinding,
    SoftschemaMetadata,
    SoftschemaProfile,
    SoftschemaStatus,
    SoftschemaWarning,
    WarningCode,
    parse_softschema_metadata,
)
from softschema.registry import SoftschemaRegistry


@dataclass(frozen=True)
class StructuralResult:
    ok: bool
    errors: list[dict[str, Any]] = field(default_factory=list)
    engine: str = "json_schema"


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
    """Validation result enriched with binding and document metadata."""

    path: Path
    contract_id: str
    status: SoftschemaStatus
    profile: SoftschemaProfile
    structural: StructuralResult
    semantic: SemanticResult
    binding: SoftschemaBinding | None = None
    document_metadata: SoftschemaMetadata | None = None
    values: dict[str, Any] | None = None
    warnings: list[SoftschemaWarning] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.structural.ok and self.semantic.ok

    @property
    def warning_codes(self) -> list[str]:
        return [warning.code for warning in self.warnings]


HostAdapter = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ValueResolver:
    """Project frontmatter into the values dict a schema validates."""

    kind: Literal["values_key", "frontmatter_root", "host_adapter"] = "values_key"
    pointer: str = "/values"
    exclude_keys: tuple[str, ...] = ()
    host_adapter: HostAdapter | None = None

    def resolve(self, frontmatter: dict[str, Any]) -> dict[str, Any]:
        if self.kind == "values_key":
            value = _walk_pointer(frontmatter, self.pointer)
        elif self.kind == "frontmatter_root":
            value = {k: v for k, v in frontmatter.items() if k not in self.exclude_keys}
        elif self.kind == "host_adapter":
            if self.host_adapter is None:
                raise ValueError("host_adapter mode requires a callable")
            value = self.host_adapter(frontmatter)
        else:
            raise ValueError(f"unknown ValueResolver kind: {self.kind}")
        if not isinstance(value, dict):
            msg = f"resolved value is {type(value).__name__}, expected dict"
            raise TypeError(msg)
        return value


def validate_structural(values: dict[str, Any], schema_yaml_path: Path) -> StructuralResult:
    """Validate values against a JSON Schema YAML or JSON sidecar."""
    schema = _read_yaml(schema_yaml_path)
    validator = Draft202012Validator(schema)
    errors = [_describe_jsonschema_error(error) for error in validator.iter_errors(values)]
    return StructuralResult(ok=not errors, errors=errors)


def validate_semantic(values: dict[str, Any], model_cls: type[BaseModel]) -> SemanticResult:
    """Validate values by calling ``model_cls.model_validate``."""
    try:
        model_cls.model_validate(values)
    except ValidationError as exc:
        return SemanticResult(ok=False, errors=[dict(error) for error in exc.errors()])
    return SemanticResult(ok=True)


def validate_values(
    values: dict[str, Any],
    *,
    model: type[BaseModel] | None = None,
    schema: Path | None = None,
) -> ValidationResult:
    """Validate a pre-extracted values dict against a model, a schema, or both.

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


def validate(
    doc_path: Path,
    *,
    model: type[BaseModel] | None = None,
    schema: Path | None = None,
    resolver: ValueResolver | None = None,
) -> ValidationResult:
    """Run structural and semantic validation against a frontmatter Markdown document."""
    if model is None and schema is None:
        raise ValueError("validate() requires at least one of model= or schema=")
    resolver = resolver or ValueResolver(kind="frontmatter_root", exclude_keys=("softschema",))

    try:
        _content, frontmatter = _read_frontmatter_doc(doc_path)
    except (FmFormatError, yaml.YAMLError) as exc:
        return ValidationResult(
            structural=StructuralResult(ok=False, errors=[_error("parse_error", str(exc))]),
            semantic=SemanticResult(ok=False, skipped_reason="parse_error"),
        )
    if frontmatter is None:
        return ValidationResult(
            structural=StructuralResult(
                ok=False,
                errors=[_error("no_frontmatter", f"no frontmatter in {doc_path}")],
            ),
            semantic=SemanticResult(ok=False, skipped_reason="no_frontmatter"),
        )
    if not isinstance(frontmatter, dict):
        return ValidationResult(
            structural=StructuralResult(
                ok=False,
                errors=[_error("frontmatter_not_mapping", "frontmatter is not a mapping")],
            ),
            semantic=SemanticResult(ok=False, skipped_reason="frontmatter_not_mapping"),
        )
    try:
        values = resolver.resolve(dict(frontmatter))
    except Exception as exc:
        return ValidationResult(
            structural=StructuralResult(ok=False, errors=[_resolver_error(resolver, exc)]),
            semantic=SemanticResult(ok=False, skipped_reason="resolver_error"),
        )

    structural = validate_structural(values, schema) if schema else StructuralResult(ok=True)
    semantic = validate_semantic(values, model) if model else SemanticResult(ok=True)
    return ValidationResult(structural=structural, semantic=semantic)


def validate_artifact(
    doc_path: Path,
    *,
    binding: SoftschemaBinding | None = None,
    contract_id: str | None = None,
    registry: SoftschemaRegistry | None = None,
    metadata_mode: Literal["enforced", "advisory"] = "enforced",
) -> ArtifactValidationResult:
    """Validate an artifact using a complete schema binding."""
    if binding is None and contract_id is not None and registry is not None:
        binding = registry.resolve(contract_id)
    if binding is None:
        resolved_contract_id = contract_id or "<unknown>"
        return ArtifactValidationResult(
            path=doc_path,
            contract_id=resolved_contract_id,
            status=SoftschemaStatus.soft,
            profile=SoftschemaProfile.frontmatter_md,
            binding=None,
            structural=StructuralResult(
                ok=False,
                errors=[
                    _error(
                        "contract_binding_missing",
                        f"no softschema binding registered for {resolved_contract_id!r}",
                        contract_id=resolved_contract_id,
                    )
                ],
            ),
            semantic=SemanticResult(ok=False, skipped_reason="contract_binding_missing"),
        )

    warnings: list[SoftschemaWarning] = []
    if binding.profile == SoftschemaProfile.pure_yaml:
        return _validate_pure_yaml_artifact(doc_path, binding, warnings)
    return _validate_frontmatter_artifact(doc_path, binding, warnings, metadata_mode)


def _validate_frontmatter_artifact(
    doc_path: Path,
    binding: SoftschemaBinding,
    warnings: list[SoftschemaWarning],
    metadata_mode: Literal["enforced", "advisory"],
) -> ArtifactValidationResult:
    try:
        _content, frontmatter = _read_frontmatter_doc(doc_path)
    except (FmFormatError, yaml.YAMLError) as exc:
        return _artifact_failure(doc_path, binding, "parse_error", str(exc))
    if frontmatter is None:
        return _artifact_failure(
            doc_path, binding, "no_frontmatter", f"no frontmatter in {doc_path}"
        )
    if not isinstance(frontmatter, dict):
        return _artifact_failure(
            doc_path,
            binding,
            "frontmatter_not_mapping",
            "frontmatter is not a mapping",
        )

    metadata_result = _metadata_from_frontmatter(
        doc_path, frontmatter, binding, warnings, metadata_mode
    )
    if isinstance(metadata_result, ArtifactValidationResult):
        return metadata_result
    metadata = metadata_result

    if binding.envelope_key is not None and binding.envelope_key not in frontmatter:
        actual_keys = [str(key) for key in frontmatter if key != "softschema"]
        return ArtifactValidationResult(
            path=doc_path,
            contract_id=binding.contract_id,
            status=binding.status,
            profile=binding.profile,
            binding=binding,
            document_metadata=metadata,
            warnings=warnings,
            structural=StructuralResult(
                ok=False,
                errors=[
                    _error(
                        "envelope_mismatch",
                        f"contract {binding.contract_id!r} expects {binding.envelope_key!r}",
                        expected_key=binding.envelope_key,
                        actual_keys=actual_keys,
                    )
                ],
            ),
            semantic=SemanticResult(ok=False, skipped_reason="envelope_mismatch"),
        )

    resolver = _resolver_for_binding(binding)
    try:
        values = resolver.resolve(frontmatter)
    except Exception as exc:
        return _resolver_failure(doc_path, binding, metadata, warnings, resolver, exc)
    return _validate_extracted_values(
        doc_path,
        binding,
        values,
        metadata=metadata,
        warnings=warnings,
    )


def _validate_pure_yaml_artifact(
    doc_path: Path,
    binding: SoftschemaBinding,
    warnings: list[SoftschemaWarning],
) -> ArtifactValidationResult:
    try:
        raw = _read_yaml(doc_path)
    except yaml.YAMLError as exc:
        return _artifact_failure(doc_path, binding, "parse_error", str(exc))
    if not isinstance(raw, dict):
        return _artifact_failure(
            doc_path,
            binding,
            "yaml_not_mapping",
            f"YAML root is {type(raw).__name__}, expected mapping",
        )
    return _validate_extracted_values(doc_path, binding, raw, metadata=None, warnings=warnings)


def _metadata_from_frontmatter(
    doc_path: Path,
    frontmatter: dict[str, Any],
    binding: SoftschemaBinding,
    warnings: list[SoftschemaWarning],
    metadata_mode: Literal["enforced", "advisory"],
) -> SoftschemaMetadata | ArtifactValidationResult | None:
    try:
        metadata = parse_softschema_metadata(frontmatter.get("softschema"))
    except (TypeError, ValidationError) as exc:
        return _artifact_failure(
            doc_path,
            binding,
            "document_softschema_invalid",
            str(exc),
            warnings=warnings,
        )
    if metadata is None:
        return None
    if metadata.contract_id != binding.contract_id:
        message = (
            f"document declares {metadata.contract_id!r}; binding uses {binding.contract_id!r}"
        )
        if metadata_mode == "advisory":
            warnings.append(
                SoftschemaWarning(code=WarningCode.DOCUMENT_CONTRACT_MISMATCH, message=message)
            )
        else:
            return _artifact_failure(
                doc_path,
                binding,
                "document_contract_mismatch",
                message,
                metadata=metadata,
                warnings=warnings,
            )
    if metadata.status is not None and metadata.status != binding.status:
        warnings.append(
            SoftschemaWarning(
                code=WarningCode.DOCUMENT_STATUS_MISMATCH,
                message=(
                    f"document declares status {metadata.status.value!r}; binding uses "
                    f"{binding.status.value!r}"
                ),
            )
        )
    return metadata


def _resolver_for_binding(binding: SoftschemaBinding) -> ValueResolver:
    if binding.envelope_key is not None:
        return ValueResolver(
            kind="values_key", pointer=f"/{_encode_json_pointer(binding.envelope_key)}"
        )
    return ValueResolver(kind="frontmatter_root", exclude_keys=("softschema",))


def _validate_extracted_values(
    doc_path: Path,
    binding: SoftschemaBinding,
    values: dict[str, Any],
    *,
    metadata: SoftschemaMetadata | None,
    warnings: list[SoftschemaWarning],
) -> ArtifactValidationResult:
    schema_path = _resolve_schema_path(binding.schema_path, doc_path)
    if binding.schema_path is not None:
        if schema_path is None:
            structural = StructuralResult(
                ok=False,
                errors=[
                    _error(
                        "schema_sidecar_missing",
                        f"schema sidecar not found: {binding.schema_path}",
                        path=str(binding.schema_path),
                    )
                ],
            )
        else:
            structural = validate_structural(values, schema_path)
    elif binding.model is not None:
        structural = StructuralResult(ok=True, engine="skipped_inferred_via_model")
    else:
        structural = StructuralResult(ok=True, engine="skipped_no_schema")

    semantic = (
        validate_semantic(values, binding.model)
        if binding.model is not None
        else SemanticResult(ok=True, skipped_reason="no_pydantic_model")
    )
    return ArtifactValidationResult(
        path=doc_path,
        contract_id=binding.contract_id,
        status=binding.status,
        profile=binding.profile,
        binding=binding,
        document_metadata=metadata,
        values=values,
        warnings=warnings,
        structural=structural,
        semantic=semantic,
    )


def _resolve_schema_path(path: Path | None, doc_path: Path) -> Path | None:
    if path is None:
        return None
    if path.exists():
        return path
    if path.is_absolute():
        return None
    for base in (doc_path.parent, Path.cwd(), *Path.cwd().parents):
        candidate = base / path
        if candidate.exists():
            return candidate
    return None


def _artifact_failure(
    doc_path: Path,
    binding: SoftschemaBinding,
    kind: str,
    message: str,
    *,
    metadata: SoftschemaMetadata | None = None,
    warnings: list[SoftschemaWarning] | None = None,
) -> ArtifactValidationResult:
    return ArtifactValidationResult(
        path=doc_path,
        contract_id=binding.contract_id,
        status=binding.status,
        profile=binding.profile,
        binding=binding,
        document_metadata=metadata,
        warnings=warnings or [],
        structural=StructuralResult(ok=False, errors=[_error(kind, message)]),
        semantic=SemanticResult(ok=False, skipped_reason=kind),
    )


def _resolver_failure(
    doc_path: Path,
    binding: SoftschemaBinding,
    metadata: SoftschemaMetadata | None,
    warnings: list[SoftschemaWarning],
    resolver: ValueResolver,
    exc: Exception,
) -> ArtifactValidationResult:
    return ArtifactValidationResult(
        path=doc_path,
        contract_id=binding.contract_id,
        status=binding.status,
        profile=binding.profile,
        binding=binding,
        document_metadata=metadata,
        warnings=warnings,
        structural=StructuralResult(ok=False, errors=[_resolver_error(resolver, exc)]),
        semantic=SemanticResult(ok=False, skipped_reason="resolver_error"),
    )


def _read_frontmatter_doc(path: Path) -> tuple[str, Any | None]:
    if path.suffix != ".gz":
        return fmf_read(path)
    with _temporary_text_artifact(path) as temp_path:
        return fmf_read(temp_path)


def _read_yaml(path: Path) -> Any:
    if path.suffix != ".gz":
        return read_yaml_file(path)
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _describe_jsonschema_error(err: JsonSchemaError) -> dict[str, Any]:
    return {
        "path": list(err.absolute_path),
        "message": err.message,
        "validator": err.validator,
        "validator_value": err.validator_value,
        "value": err.instance,
    }


def _walk_pointer(obj: Any, pointer: str) -> Any:
    if not pointer or pointer == "/":
        return obj
    cur = obj
    for raw_segment in pointer.lstrip("/").split("/"):
        segment = _decode_json_pointer(raw_segment)
        if isinstance(cur, dict):
            if segment not in cur:
                raise KeyError(f"pointer segment {segment!r} missing in dict")
            cur = cur[segment]
        elif isinstance(cur, list):
            cur = cur[int(segment)]
        else:
            raise TypeError(f"cannot walk pointer into {type(cur).__name__}")
    return cur


def _encode_json_pointer(segment: str) -> str:
    return segment.replace("~", "~0").replace("/", "~1")


def _decode_json_pointer(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def _error(kind: str, message: str, **details: Any) -> dict[str, Any]:
    return {"kind": kind, "message": message, **details}


def _resolver_error(resolver: ValueResolver, exc: Exception) -> dict[str, Any]:
    return _error(
        "resolver_error",
        str(exc),
        resolver_kind=resolver.kind,
        resolver_pointer=resolver.pointer,
        exception_type=type(exc).__name__,
    )


@contextmanager
def _temporary_text_artifact(path: Path):
    suffix = path.with_suffix("").suffix
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=suffix) as tmp:
            with gzip.open(path, "rt", encoding="utf-8") as src:
                tmp.write(src.read())
            temp_path = Path(tmp.name)
        yield temp_path
    finally:
        if temp_path is not None:
            with suppress(OSError):
                temp_path.unlink()
