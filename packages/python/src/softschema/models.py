"""Public contract and metadata models for softschema."""

from __future__ import annotations

import re
from enum import StrEnum
from ipaddress import AddressValueError, IPv4Address, IPv6Address
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

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

from softschema.value_domain import normalize_portable_value

ARTIFACT_FORMAT_VERSION = "1"

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
_REVERSE_DNS_NAMESPACE_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$"
)
_LEGACY_AUTHORED_METADATA_KEYS = frozenset({"contract", "schema", "envelope", "status"})
_FORMAT_1_AUTHORED_METADATA_KEYS = _LEGACY_AUTHORED_METADATA_KEYS | {
    "format",
    "extensions",
}


def validate_contract_id(value: object) -> str:
    """Return a valid logical contract ID or raise ``ValueError``.

    This is the single contract-ID grammar boundary used by metadata, contracts,
    registries, compilers, and explicit CLI overrides.
    """
    if not isinstance(value, str) or not _CONTRACT_ID_RE.fullmatch(value):
        raise ValueError(
            f"malformed contract ID {value!r}: expected [namespace:]Name[/version] "
            "(namespace lowercase [a-z0-9_], dot-separated; name starts with a letter "
            "or underscore; at most one ':' and one '/'; no whitespace)"
        )
    return value


_URN_RE = re.compile(
    r"^urn:([a-z0-9]|[a-z0-9][a-z0-9-]{0,30}[a-z0-9]):"
    r"([A-Za-z0-9._~!$&'()*+,;=:@/%-]+)$"
)
_PERCENT_ESCAPE_RE = re.compile(r"%([0-9A-Fa-f]{2})")
_URI_ASCII_RE = re.compile(r"^[A-Za-z0-9:/?\[\]@!$&'()*+,;=._~%-]+$")
_HTTPS_PATH_RE = re.compile(r"^[A-Za-z0-9._~!$&'()*+,;=:@/%-]*$")
_HTTPS_QUERY_RE = re.compile(r"^[A-Za-z0-9._~!$&'()*+,;=:@/?%-]*$")
_IPV4_NUMBER_RE = re.compile(r"^(?:0[xX][0-9A-Fa-f]+|[0-9]+)$")
_UNRESERVED_BYTES = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


def _has_canonical_percent_escapes(value: str) -> bool:
    """Whether every escape is valid, uppercase, and not an encoded unreserved byte."""
    matches = list(_PERCENT_ESCAPE_RE.finditer(value))
    if value.count("%") != len(matches):
        return False
    return all(
        match.group(1) == match.group(1).upper()
        and int(match.group(1), 16) not in _UNRESERVED_BYTES
        for match in matches
    )


def _has_canonical_https_port(netloc: str, hostname: str, port: int | None) -> bool:
    """Reject an empty, zero-padded, or default HTTPS port."""
    if netloc.startswith("["):
        closing_bracket = netloc.find("]")
        suffix = netloc[closing_bracket + 1 :] if closing_bracket >= 0 else netloc
    else:
        suffix = netloc[len(hostname) :]
    if not suffix:
        return True
    if not suffix.startswith(":"):
        return False
    port_text = suffix[1:]
    return port is not None and port != 443 and port_text.isdecimal() and port_text == str(port)


def _canonical_https_host(hostname: str) -> str | None:
    """Return the byte-canonical host spelling, or ``None`` when it is ambiguous."""
    if "%" in hostname:
        return None
    if ":" in hostname:
        try:
            return f"[{IPv6Address(hostname).compressed}]"
        except AddressValueError:
            return None
    if all(_IPV4_NUMBER_RE.fullmatch(label) for label in hostname.split(".")):
        try:
            return str(IPv4Address(hostname))
        except AddressValueError:
            return None
    return hostname


def validate_schema_id(value: object) -> str:
    """Return a canonical absolute HTTPS or URN schema identifier.

    The accepted profile is deliberately narrower than arbitrary URI references:
    lowercase scheme/authority (or URN namespace), no credentials, default port,
    dot segments, non-ASCII bytes, or fragment, and canonical percent escapes.
    """
    if not isinstance(value, str):
        raise ValueError(
            f"malformed schema ID {value!r}: expected a canonical absolute HTTPS or URN "
            "identifier without a fragment"
        )
    valid = bool(value) and _URI_ASCII_RE.fullmatch(value) is not None
    valid = valid and "#" not in value and "\\" not in value
    valid = valid and _has_canonical_percent_escapes(value)
    if valid and value.startswith("urn:"):
        valid = _URN_RE.fullmatch(value) is not None
    elif valid and value.startswith("https://"):
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            valid = False
        else:
            path_segments = parsed.path.split("/")
            canonical_host = _canonical_https_host(parsed.hostname) if parsed.hostname else None
            canonical_netloc = canonical_host
            if canonical_netloc is not None and port is not None:
                canonical_netloc = f"{canonical_netloc}:{port}"
            valid = (
                parsed.scheme == "https"
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and parsed.netloc == parsed.netloc.lower()
                and parsed.netloc == canonical_netloc
                and not parsed.hostname.endswith(".")
                and _has_canonical_https_port(parsed.netloc, parsed.hostname, port)
                and parsed.path.startswith("/")
                and _HTTPS_PATH_RE.fullmatch(parsed.path) is not None
                and _HTTPS_QUERY_RE.fullmatch(parsed.query) is not None
                and "." not in path_segments
                and ".." not in path_segments
                and not value.endswith(("?", "#"))
                and parsed.geturl() == value
            )
    else:
        valid = False
    if not valid:
        raise ValueError(
            f"malformed schema ID {value!r}: expected a canonical absolute HTTPS or URN "
            "identifier without a fragment"
        )
    return value


def validate_extension_namespace(value: object) -> str:
    """Return a canonical format-1 extension namespace or raise ``ValueError``."""
    if isinstance(value, str) and _REVERSE_DNS_NAMESPACE_RE.fullmatch(value):
        return value
    if isinstance(value, str) and value.startswith("https://"):
        try:
            return validate_schema_id(value)
        except ValueError:
            pass
    raise ValueError(
        f"invalid softschema extension namespace {value!r}: expected canonical HTTPS "
        "or lowercase reverse-DNS"
    )


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

    Legacy metadata recognizes the self-description quartet: ``contract`` (what),
    ``schema`` (where the compiled schema lives), ``envelope`` (which top-level
    key carries the payload), and ``status`` (how strictly to validate). Format 1
    adds the quoted ``format: "1"`` discriminator and one opaque ``extensions`` map.
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
    format_version: Literal["1"] | None = Field(alias="format", default=None)
    extensions: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_format_shape(cls, value: Any, info: ValidationInfo) -> Any:
        if not isinstance(value, dict):
            return value

        authored = bool(info.context and info.context.get("authored"))
        has_format = "format" in value
        if authored:
            if has_format and value["format"] != ARTIFACT_FORMAT_VERSION:
                raise ValueError('softschema metadata format must be the quoted string "1"')
            authored_keys = (
                _FORMAT_1_AUTHORED_METADATA_KEYS if has_format else _LEGACY_AUTHORED_METADATA_KEYS
            )
            unknown = [key for key in value if key not in authored_keys]
            if unknown:
                rendered = ", ".join(str(key) for key in unknown)
                raise ValueError(f"softschema metadata has unknown keys: {rendered}")
            format_value = value.get("format")
        else:
            format_value = value.get("format", value.get("format_version"))
        if format_value is not None and format_value != ARTIFACT_FORMAT_VERSION:
            raise ValueError('softschema metadata format must be the quoted string "1"')
        if "extensions" in value:
            if format_value != ARTIFACT_FORMAT_VERSION:
                raise ValueError('softschema metadata extensions require format "1"')
            if not isinstance(value["extensions"], dict):
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
    def _serialize_grammar(
        self,
        handler: SerializerFunctionWrapHandler,
        info: SerializationInfo,
    ) -> dict[str, Any]:
        data = handler(self)
        if self.format_version is None:
            data.pop("format", None)
            data.pop("format_version", None)
            data.pop("extensions", None)
        elif self.extensions is None:
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
