"""Public contract and metadata models for softschema."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    ValidationInfo,
    field_validator,
    model_serializer,
    model_validator,
)

from softschema.core.identity import (
    validate_contract_id as validate_contract_id,
)
from softschema.core.identity import (
    validate_extension_namespace as validate_extension_namespace,
)
from softschema.core.identity import (
    validate_schema_id as validate_schema_id,
)
from softschema.core.metadata import (
    SchemaProfile as SchemaProfile,
)
from softschema.core.metadata import (
    SchemaStatus as SchemaStatus,
)
from softschema.core.value_domain import normalize_portable_value

_AUTHORED_METADATA_KEYS = frozenset({"contract", "schema", "envelope", "status", "extensions"})


class SchemaMetadata(BaseModel):
    """Optional document-level ``softschema:`` metadata.

    Metadata recognizes the self-description quartet: ``contract`` (what),
    ``schema`` (where the compiled schema lives), ``envelope`` (which top-level
    key carries the payload), and ``status`` (how strictly to validate), plus one
    opaque ``extensions`` map.
    The spec makes unknown keys in the ``softschema:`` block a validation error
    (``extra="forbid"``), and a contract ID must match the enforced grammar
    (see ``validate_contract_id``).

    ``schema_ref`` is aliased because a field literally named ``schema`` would
    shadow the deprecated ``BaseModel.schema`` method; the YAML key is ``schema``.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    contract_id: str = Field(alias="contract", min_length=1)
    schema_ref: str | None = Field(alias="schema", default=None, min_length=1)
    envelope: str | None = Field(default=None, min_length=1)
    status: SchemaStatus | None = None
    extensions: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_authored_shape(cls, value: Any, info: ValidationInfo) -> Any:
        if not isinstance(value, dict):
            return value

        authored = bool(info.context and info.context.get("authored"))
        if authored:
            unknown = [key for key in value if key not in _AUTHORED_METADATA_KEYS]
            if unknown:
                rendered = ", ".join(str(key) for key in unknown)
                raise ValueError(f"softschema metadata has unknown keys: {rendered}")
        if "extensions" in value and not isinstance(value["extensions"], dict):
            raise ValueError("softschema metadata extensions must be a mapping")
        return value

    @field_validator("contract_id")
    @classmethod
    def _validate_contract_id(cls, value: str) -> str:
        return validate_contract_id(value)

    @field_validator("extensions")
    @classmethod
    def _validate_extensions(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        for namespace in value:
            validate_extension_namespace(namespace)
        normalized, _size = normalize_portable_value(value)
        if not isinstance(normalized, dict):  # pragma: no cover - guarded above
            raise ValueError("softschema metadata extensions must be a mapping")
        return normalized

    @model_serializer(mode="wrap")
    def _serialize_metadata(
        self,
        handler: SerializerFunctionWrapHandler,
        info: SerializationInfo,
    ) -> dict[str, Any]:
        data = handler(self)
        if self.extensions is None:
            data.pop("extensions", None)
        return data


class Contract(BaseModel):
    """One artifact payload contract: how to validate a document with this id."""

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    id: str
    model: type[BaseModel] | None = None
    envelope_key: str | None = None
    status: SchemaStatus = SchemaStatus.soft
    profile: SchemaProfile = SchemaProfile.frontmatter_md
    schema_path: Path | None = None

    @field_validator("id")
    @classmethod
    def _validate_contract_id(cls, value: str) -> str:
        return validate_contract_id(value)


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
        return SchemaMetadata.model_validate({"contract": raw}, context={"authored": True})
    if isinstance(raw, dict):
        return SchemaMetadata.model_validate(raw, context={"authored": True})
    msg = f"softschema metadata must be a string or mapping, got {type(raw).__name__}"
    raise ValueError(msg)
