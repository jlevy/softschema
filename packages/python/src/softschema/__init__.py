"""Soft schema conventions and validation tools for Markdown/YAML artifacts."""

from __future__ import annotations

from softschema.compile import CompileResult, compile_model
from softschema.conform import ConformResult, conform_artifact
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
from softschema.pipeline import repair_and_validate_artifact
from softschema.registry import Contracts
from softschema.repair import RepairResult, repair_artifact, repair_yaml_text
from softschema.schema_view import FieldInfo, SchemaView
from softschema.soft_field import (
    RepairKind,
    SoftField,
    SoftOwner,
    SoftTier,
)
from softschema.validate import (
    ArtifactValidationResult,
    EnvelopeAmbiguityError,
    SemanticResult,
    StructuralResult,
    ValidationResult,
    clear_validator_cache,
    infer_envelope_key,
    read_frontmatter_doc,
    read_yaml_doc,
    resolve_bound_schema,
    validate_artifact,
    validate_semantic,
    validate_structural,
    validate_values,
)

__all__ = [
    "ArtifactValidationResult",
    "CompileResult",
    "ConformResult",
    "Contract",
    "Contracts",
    "EnvelopeAmbiguityError",
    "FieldInfo",
    "GeneratedSection",
    "RegenerateResult",
    "RepairKind",
    "RepairResult",
    "SchemaMetadata",
    "SchemaProfile",
    "SchemaStatus",
    "SchemaView",
    "SchemaWarning",
    "SemanticResult",
    "SoftField",
    "SoftOwner",
    "SoftTier",
    "StructuralResult",
    "ValidationResult",
    "WarningCode",
    "clear_validator_cache",
    "compile_model",
    "conform_artifact",
    "infer_envelope_key",
    "parse_schema_metadata",
    "read_frontmatter_doc",
    "read_yaml_doc",
    "regenerate",
    "repair_and_validate_artifact",
    "repair_artifact",
    "repair_yaml_text",
    "resolve_bound_schema",
    "validate_artifact",
    "validate_semantic",
    "validate_structural",
    "validate_values",
]
