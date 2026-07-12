"""Public contract and metadata models for softschema."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Enforced contract-ID grammar (the spec's "shape", independent of `status`):
#   contract-id = [ namespace ":" ] name [ "/" version ]
#   namespace   = segment *( "." segment )   ; segment = [a-z0-9_]+
#   name        = [A-Za-z_][A-Za-z0-9_]*
#   version     = [A-Za-z0-9_.-]+
# At most one ":" and one "/", no whitespace, no empty segments. Style (UpperCamelCase
# name, reverse-DNS namespace, short version) stays advisory and is not checked here.
_CONTRACT_ID_RE = re.compile(
    r"^(?:[a-z0-9_]+(?:\.[a-z0-9_]+)*:)?[A-Za-z_][A-Za-z0-9_]*(?:/[A-Za-z0-9_.-]+)?$"
)


def _check_contract_id(value: str) -> str:
    """Raise if ``value`` violates the enforced contract-ID grammar."""
    if not _CONTRACT_ID_RE.match(value):
        raise ValueError(
            f"malformed contract ID {value!r}: expected [namespace:]Name[/version] "
            "(namespace lowercase [a-z0-9_], dot-separated; name starts with a letter "
            "or underscore; at most one ':' and one '/'; no whitespace)"
        )
    return value


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
    """Optional document-level ``softschema:`` metadata.

    The recognized keys are the self-description quartet: ``contract`` (what),
    ``schema`` (where the compiled schema lives), ``envelope`` (which top-level
    key carries the payload), and ``status`` (how strictly to validate).
    The spec makes unknown keys in the ``softschema:`` block a validation error
    (``extra="forbid"``), and a contract ID must match the enforced grammar
    (see ``_check_contract_id``).

    ``schema_ref`` is aliased because a field literally named ``schema`` would
    shadow the deprecated ``BaseModel.schema`` method; the YAML key is ``schema``.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    contract_id: str = Field(alias="contract", min_length=1)
    schema_ref: str | None = Field(alias="schema", default=None, min_length=1)
    envelope: str | None = Field(default=None, min_length=1)
    status: SchemaStatus | None = None

    @field_validator("contract_id")
    @classmethod
    def _validate_contract_id(cls, value: str) -> str:
        return _check_contract_id(value)


class Contract(BaseModel):
    """One artifact payload contract: how to validate a document with this id."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    model: type[BaseModel] | None = None
    envelope_key: str | None = None
    status: SchemaStatus = SchemaStatus.soft
    profile: SchemaProfile = SchemaProfile.frontmatter_md
    schema_path: Path | None = None

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return _check_contract_id(value)


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
    raise ValueError(msg)
