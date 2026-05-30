"""Per-field ``x-softschema`` annotations for Pydantic source models.

`SoftField` is a thin wrapper around Pydantic's ``Field`` that records authoring
metadata (group, tier, owner, instruction, examples, aliases, repair) under the
field's ``json_schema_extra``. The compiler propagates it verbatim into the
generated JSON Schema sidecar as a per-property ``x-softschema:`` block; the
runtime never uses it for validation.

`SoftField` is optional. Reach for it per field, only when a specific downstream
consumer reads a specific metadata key. A model whose only consumer is
``validate_artifact()`` does not need it; plain ``Field`` is enough.

The consumers that earn `SoftField` annotations are:

- A template generator that emits section headers from ``group`` and inline
  hints from ``instruction`` / ``examples``.
- An agent prompt builder that filters by ``owner`` to hide system- or
  postprocess-filled fields.
- A tier-aware QA harness that routes checks by ``tier``.
- Generated runbook sections (``softschema generate``) keyed by ``group`` or a
  specific pointer.

Blanket-annotating every field without a consumer in mind is per-field clutter
that never pays back. Add `SoftField` field by field as the consumer that reads it
lands.
"""

from __future__ import annotations

from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

SoftOwner: TypeAlias = Literal["agent", "postprocess", "system", "human"]
"""Who or what produces the value at runtime."""

SoftTier: TypeAlias = Literal["hard_fact", "constrained", "narrative"]
"""How rigorously the field should be treated by reviewers and QA."""

RepairKind: TypeAlias = Literal["none", "safe_coerce", "suggest_alias"]
"""How a future repair pass may treat near-miss values for the field."""


class SoftFieldMeta(BaseModel):
    """Structured metadata block written under ``x-softschema`` on each field."""

    model_config = ConfigDict(extra="forbid")

    group: str
    order: int | None = None
    tier: SoftTier | None = None
    owner: SoftOwner = "agent"
    instruction: str | None = None
    examples: list[Any] = Field(default_factory=list)
    aliases: dict[str, list[str]] = Field(default_factory=dict)
    repair: RepairKind = "none"


def SoftField(
    *,
    description: str,
    group: str,
    owner: SoftOwner = "agent",
    tier: SoftTier | None = None,
    order: int | None = None,
    instruction: str | None = None,
    examples: list[Any] | None = None,
    aliases: dict[str, list[str]] | None = None,
    repair: RepairKind = "none",
    **field_kwargs: Any,
) -> Any:
    """Return a Pydantic ``Field`` carrying an ``x-softschema`` annotation.

    See the module docstring for when `SoftField` is worth reaching for over plain
    ``Field``.

    Pass any additional Pydantic ``Field`` kwargs (such as ``default``,
    ``ge``, ``min_length``) via ``**field_kwargs``. The annotation lands under
    ``json_schema_extra`` so the standard ``model_json_schema()`` flow (and the
    softschema compiler that wraps it) emits it as a per-property
    ``x-softschema`` block in the JSON Schema sidecar.

    Empty optional values are omitted from the emitted metadata so the sidecar
    stays minimal.
    """
    meta = SoftFieldMeta(
        group=group,
        order=order,
        tier=tier,
        owner=owner,
        instruction=instruction,
        examples=examples or [],
        aliases=aliases or {},
        repair=repair,
    )
    annotation = meta.model_dump(exclude_none=True)
    if not annotation.get("examples"):
        annotation.pop("examples", None)
    if not annotation.get("aliases"):
        annotation.pop("aliases", None)
    if annotation.get("repair") == "none":
        annotation.pop("repair", None)
    return Field(
        description=description,
        json_schema_extra={"x-softschema": annotation},
        **field_kwargs,
    )
