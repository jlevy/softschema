"""Soft schema conventions and validation tools for Markdown/YAML artifacts."""

from __future__ import annotations

from softschema.compile import SOFTSCHEMA_FORMAT_VERSION, CompileResult, compile_model
from softschema.models import (
    SoftschemaBinding,
    SoftschemaMetadata,
    SoftschemaProfile,
    SoftschemaStage,
    SoftschemaStatus,
    SoftschemaWarning,
    parse_softschema_metadata,
)
from softschema.registry import SoftschemaRegistry
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
    "SoftschemaProfile",
    "ArtifactValidationResult",
    "CompileResult",
    "SoftschemaMetadata",
    "SoftschemaBinding",
    "SoftschemaRegistry",
    "SemanticResult",
    "SoftschemaStatus",
    "StructuralResult",
    "SoftschemaStage",
    "ValidationResult",
    "SoftschemaWarning",
    "ValueResolver",
    "compile_model",
    "parse_softschema_metadata",
    "validate",
    "validate_artifact",
    "validate_semantic",
    "validate_structural",
    "validate_values",
]
