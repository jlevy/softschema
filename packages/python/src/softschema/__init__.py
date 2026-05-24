"""Soft schema conventions and validation tools for Markdown/YAML artifacts."""

from __future__ import annotations

from softschema.compile import SOFTSCHEMA_FORMAT_VERSION, CompileResult, compile_model
from softschema.models import (
    ArtifactProfile,
    DocumentMetadata,
    SchemaBinding,
    Status,
    StructureStage,
    ValidationWarning,
    parse_document_metadata,
)
from softschema.registry import SchemaRegistry
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
    "ArtifactProfile",
    "ArtifactValidationResult",
    "CompileResult",
    "DocumentMetadata",
    "SchemaBinding",
    "SchemaRegistry",
    "SemanticResult",
    "Status",
    "StructuralResult",
    "StructureStage",
    "ValidationResult",
    "ValidationWarning",
    "ValueResolver",
    "compile_model",
    "parse_document_metadata",
    "validate",
    "validate_artifact",
    "validate_semantic",
    "validate_structural",
    "validate_values",
]
