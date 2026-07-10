"""JSON-compatible normalized validation result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
