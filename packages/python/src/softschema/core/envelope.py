"""Portable artifact-envelope selection."""

from __future__ import annotations

from typing import Any


class EnvelopeAmbiguityError(ValueError):
    """Multiple top-level payload candidates; the envelope must be designated."""

    def __init__(self, candidates: list[str]) -> None:
        self.candidates = candidates
        super().__init__(
            "multiple top-level frontmatter keys; designate the softschema payload "
            f"(candidates: {', '.join(candidates)})"
        )


def infer_envelope_key(frontmatter: dict[str, Any]) -> str | None:
    """Return the only non-metadata key, or require explicit disambiguation."""
    candidates = [key for key in frontmatter if key != "softschema"]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    raise EnvelopeAmbiguityError(candidates)
