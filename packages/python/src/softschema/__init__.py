"""Soft schema conventions and validation tools for Markdown/YAML artifacts."""

from __future__ import annotations

from softschema.compile import SOFTSCHEMA_FORMAT_VERSION, CompileResult, compile_model
from softschema.generate import GeneratedSection, RegenerateResult, regenerate
from softschema.models import (
    Contract,
    SchemaMetadata,
    SchemaProfile,
    SchemaStage,
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
    SemanticResult,
    StructuralResult,
    ValidationResult,
    ValueResolver,
    validate,
    validate_artifact,
    validate_semantic,
    validate_structural,
    validate_values,
)

__all__ = [
    "SOFTSCHEMA_FORMAT_VERSION",
    "SchemaProfile",
    "ArtifactValidationResult",
    "CompileResult",
    "SchemaMetadata",
    "Contract",
    "Contracts",
    "SemanticResult",
    "SchemaStatus",
    "StructuralResult",
    "SchemaStage",
    "ValidationResult",
    "SchemaWarning",
    "FieldInfo",
    "GeneratedSection",
    "RegenerateResult",
    "RepairKind",
    "SchemaView",
    "SoftField",
    "SoftFieldMeta",
    "SoftOwner",
    "SoftTier",
    "ValueResolver",
    "WarningCode",
    "compile_model",
    "parse_schema_metadata",
    "regenerate",
    "validate",
    "validate_artifact",
    "validate_semantic",
    "validate_structural",
    "validate_values",
]
