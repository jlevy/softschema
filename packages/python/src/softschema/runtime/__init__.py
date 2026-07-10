"""Python runtime adapters for YAML, filesystems, Pydantic, and packaged resources.

The package root keeps re-exporting these objects for compatibility. New integrations
that need only JSON-compatible contract semantics should depend on ``softschema.core``.
"""

from __future__ import annotations

from softschema.compile import SOFTSCHEMA_FORMAT_VERSION, CompileResult, compile_model
from softschema.models import Contract, SchemaMetadata, parse_schema_metadata
from softschema.schema_view import FieldInfo, SchemaView
from softschema.validate import (
    ArtifactFrontmatterError,
    ArtifactInputReason,
    ArtifactParseReason,
    ArtifactRootError,
    ArtifactValidationResult,
    SchemaResource,
    SchemaResources,
    artifact_error_record,
    artifact_input_error_record,
    artifact_parse_error_record,
    read_frontmatter,
    read_yaml_artifact,
    validate_artifact,
    validate_semantic,
    validate_structural,
    validate_values,
)
from softschema.value_domain import (
    PortableValueError,
    PortableYamlError,
    PortableYamlSyntaxError,
    parse_portable_yaml,
)

__all__ = [
    "SOFTSCHEMA_FORMAT_VERSION",
    "ArtifactFrontmatterError",
    "ArtifactInputReason",
    "ArtifactParseReason",
    "ArtifactRootError",
    "ArtifactValidationResult",
    "CompileResult",
    "Contract",
    "FieldInfo",
    "PortableValueError",
    "PortableYamlError",
    "PortableYamlSyntaxError",
    "SchemaMetadata",
    "SchemaResource",
    "SchemaResources",
    "SchemaView",
    "artifact_error_record",
    "artifact_input_error_record",
    "artifact_parse_error_record",
    "compile_model",
    "parse_portable_yaml",
    "parse_schema_metadata",
    "read_frontmatter",
    "read_yaml_artifact",
    "validate_artifact",
    "validate_semantic",
    "validate_structural",
    "validate_values",
]
