"""Soft schema conventions and validation tools for Markdown/YAML artifacts."""

from __future__ import annotations

from softschema.canonicalize import apply_enforced_extras, canonicalize_json_schema
from softschema.compile import SOFTSCHEMA_FORMAT_VERSION, CompileResult, compile_model
from softschema.generate import GeneratedSection, RegenerateResult, regenerate
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
from softschema.schema_view import FieldInfo, SchemaView
from softschema.soft_field import (
    RepairKind,
    SoftField,
    SoftFieldMeta,
    SoftOwner,
    SoftTier,
)
from softschema.validate import (
    ArtifactValidationResult,
    EnvelopeAmbiguityError,
    SemanticResult,
    StructuralResult,
    ValidationResult,
    infer_envelope_key,
    validate_artifact,
    validate_semantic,
    validate_structural,
    validate_values,
)

__all__ = [
    "SOFTSCHEMA_FORMAT_VERSION",
    "ArtifactValidationResult",
    "CompileResult",
    "Contract",
    "Contracts",
    "EnvelopeAmbiguityError",
    "FieldInfo",
    "GeneratedSection",
    "RegenerateResult",
    "RepairKind",
    "SchemaMetadata",
    "SchemaProfile",
    "SchemaStatus",
    "SchemaView",
    "SchemaWarning",
    "SemanticResult",
    "SoftField",
    "SoftFieldMeta",
    "SoftOwner",
    "SoftTier",
    "StructuralResult",
    "ValidationResult",
    "WarningCode",
    "apply_enforced_extras",
    "canonicalize_json_schema",
    "compile_model",
    "infer_envelope_key",
    "parse_schema_metadata",
    "regenerate",
    "validate_artifact",
    "validate_semantic",
    "validate_structural",
    "validate_values",
]
