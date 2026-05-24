"""Public binding and metadata models for softschema."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Status(StrEnum):
    """How strongly a project treats a soft schema at a boundary."""

    soft = "soft"
    permissive = "permissive"
    enforced = "enforced"


class ArtifactProfile(StrEnum):
    """Storage shape for an artifact."""

    frontmatter_md = "frontmatter-md"
    pure_yaml = "pure-yaml"


class StructureStage(StrEnum):
    """Coarse position on the structure continuum."""

    prose = "prose"
    frontmatter = "frontmatter"
    validated_frontmatter = "validated_frontmatter"
    pure_data = "pure_data"


class DocumentMetadata(BaseModel):
    """Optional document-level ``softschema:`` metadata."""

    model_config = ConfigDict(populate_by_name=True)

    contract_id: str = Field(alias="contract")
    status: Status | None = None


class SchemaBinding(BaseModel):
    """Contract between an artifact payload and an implementation schema."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    contract_id: str
    model: type[BaseModel] | None = None
    envelope_key: str | None = None
    status: Status = Status.soft
    owner: str | None = None
    profile: ArtifactProfile = ArtifactProfile.frontmatter_md
    schema_path: Path | None = None

    @property
    def stage(self) -> StructureStage:
        if self.profile == ArtifactProfile.pure_yaml:
            return StructureStage.pure_data
        if self.model is not None or self.schema_path is not None:
            return StructureStage.validated_frontmatter
        if self.envelope_key is not None:
            return StructureStage.frontmatter
        return StructureStage.prose


class ValidationWarning(BaseModel):
    """Structured non-fatal warning emitted by validation."""

    code: str
    message: str
    severity: Literal["info", "warning"] = "warning"


def parse_document_metadata(raw: Any) -> DocumentMetadata | None:
    """Parse compact or expanded document-level ``softschema:`` metadata."""
    if raw is None:
        return None
    if isinstance(raw, str):
        return DocumentMetadata.model_validate({"contract": raw})
    if isinstance(raw, dict):
        return DocumentMetadata.model_validate(raw)
    msg = f"softschema metadata must be a string or mapping, got {type(raw).__name__}"
    raise TypeError(msg)
