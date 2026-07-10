"""JSON-compatible normalized validation result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, NotRequired, Required, TypedDict

from softschema.core.value_domain import JsonValue

ArtifactInputReasonWire = Literal[
    "not_found",
    "unreadable",
    "directory_requires_recursive",
    "no_matches",
    "discovery_limit",
]
ArtifactParseReasonWire = Literal["frontmatter", "syntax", "root", "value_domain"]


class ArtifactInputSuccessWire(TypedDict):
    """Successful artifact-input-v1 wire value."""

    kind: Literal["artifact_input"]
    ok: Literal[True]
    source: str
    profile: Literal["frontmatter-md", "pure-yaml"]
    values: dict[str, JsonValue]


class ArtifactParseErrorWire(TypedDict):
    """Readable artifact parse failure."""

    kind: Required[Literal["parse_error"]]
    reason: Required[ArtifactParseReasonWire]
    message: Required[str]
    source: Required[str]
    path: NotRequired[str]
    line: NotRequired[int]
    column: NotRequired[int]


class ArtifactInputErrorWire(TypedDict):
    """Artifact access or discovery failure."""

    kind: Literal["input_error"]
    reason: ArtifactInputReasonWire
    message: str
    source: str


ArtifactInputResultWire = ArtifactInputSuccessWire | ArtifactParseErrorWire | ArtifactInputErrorWire


@dataclass(frozen=True)
class StructuralResult:
    """Portable structural-validation outcome."""

    ok: bool
    errors: list[dict[str, Any]] = field(default_factory=list)
    engine: str = "json_schema"
    skipped_reason: str | None = None


@dataclass(frozen=True)
class SemanticResult:
    """Runtime semantic-validation outcome."""

    ok: bool
    errors: list[dict[str, Any]] = field(default_factory=list)
    skipped_reason: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Combined structural and semantic outcome."""

    structural: StructuralResult
    semantic: SemanticResult

    @property
    def ok(self) -> bool:
        return self.structural.ok and self.semantic.ok
