"""Public contract and metadata models for softschema."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SchemaStatus(StrEnum):
    """How strongly a project treats a soft schema at a boundary."""

    soft = "soft"
    permissive = "permissive"
    enforced = "enforced"


class SchemaProfile(StrEnum):
    """Storage shape for an artifact."""

    frontmatter_md = "frontmatter-md"
    pure_yaml = "pure-yaml"


class SchemaMetadata(BaseModel):
    """Optional document-level ``softschema:`` metadata."""

    model_config = ConfigDict(populate_by_name=True)

    contract_id: str = Field(alias="contract")
    status: SchemaStatus | None = None


class Contract(BaseModel):
    """One artifact payload contract: how to validate a document with this id."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    model: type[BaseModel] | None = None
    envelope_key: str | None = None
    status: SchemaStatus = SchemaStatus.soft
    profile: SchemaProfile = SchemaProfile.frontmatter_md
    schema_path: Path | None = None


class WarningCode(StrEnum):
    """Stable, public identifiers for warnings emitted by validation.

    Every public warning code uses the ``document-*`` prefix so downstream code
    can filter the family with a single check (``code.startswith("document-")``).
    Adding a new public code requires both an enum member here and a row in the
    Warning Codes section of ``docs/softschema-python-design.md``.
    """

    DOCUMENT_CONTRACT_MISMATCH = "document-contract-mismatch"
    DOCUMENT_STATUS_MISMATCH = "document-status-mismatch"


class SchemaWarning(BaseModel):
    """Structured non-fatal warning emitted by validation."""

    code: str
    message: str
    severity: Literal["info", "warning"] = "warning"


def parse_schema_metadata(raw: Any) -> SchemaMetadata | None:
    """Parse compact or expanded document-level ``softschema:`` metadata."""
    if raw is None:
        return None
    if isinstance(raw, str):
        return SchemaMetadata.model_validate({"contract": raw})
    if isinstance(raw, dict):
        return SchemaMetadata.model_validate(raw)
    msg = f"softschema metadata must be a string or mapping, got {type(raw).__name__}"
    raise TypeError(msg)
