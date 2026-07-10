"""Per-field ``x-softschema`` annotations for Pydantic source models.

`SoftField` is a thin wrapper around Pydantic's ``Field`` that records authoring
metadata (group, tier, owner, instruction, examples, aliases, repair) under the
field's ``json_schema_extra``. The compiler propagates it verbatim into the
compiled JSON Schema as a per-property ``x-softschema:`` block; the
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

import math
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

SoftOwner: TypeAlias = Literal["agent", "postprocess", "system", "human"]
"""Who or what produces the value at runtime."""

SoftTier: TypeAlias = Literal["hard_fact", "constrained", "narrative"]
"""How rigorously the field should be treated by reviewers and QA."""

RepairKind: TypeAlias = Literal["none", "safe_coerce", "suggest_alias"]
"""How a future repair pass may treat near-miss values for the field."""

_SOFT_OWNERS: tuple[SoftOwner, ...] = ("agent", "postprocess", "system", "human")
_SOFT_TIERS: tuple[SoftTier, ...] = ("hard_fact", "constrained", "narrative")
_REPAIR_KINDS: tuple[RepairKind, ...] = ("none", "safe_coerce", "suggest_alias")
_GROUP_ERROR = "soft field annotation group must be a non-empty string"
_INSTRUCTION_ERROR = "soft field annotation instruction must be a non-empty string"
_ORDER_ERROR = "soft field annotation order must be an integer"
_OWNER_ERROR = "soft field annotation owner must be one of: agent, postprocess, system, human"
_TIER_ERROR = "soft field annotation tier must be one of: hard_fact, constrained, narrative"
_REPAIR_ERROR = "soft field annotation repair must be one of: none, safe_coerce, suggest_alias"
_EXAMPLES_ERROR = "soft field annotation examples must be an array"
_ALIASES_ERROR = "soft field annotation aliases must be an object of string arrays"
_NonEmptyString: TypeAlias = Annotated[str, StringConstraints(min_length=1)]


class SoftFieldMeta(BaseModel):
    """Structured metadata block written under ``x-softschema`` on each field."""

    model_config = ConfigDict(extra="forbid")

    group: _NonEmptyString
    order: int | None = None
    tier: SoftTier | None = None
    owner: SoftOwner = "agent"
    instruction: _NonEmptyString | None = None
    examples: list[Any] = Field(default_factory=list)
    aliases: dict[str, list[str]] = Field(default_factory=dict)
    repair: RepairKind = "none"

    @field_validator("group", mode="before")
    @classmethod
    def validate_group(cls, value: object) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError(_GROUP_ERROR)
        return value

    @field_validator("instruction", mode="before")
    @classmethod
    def validate_instruction(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value:
            raise ValueError(_INSTRUCTION_ERROR)
        return value

    @field_validator("order", mode="before")
    @classmethod
    def validate_order(cls, value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError(_ORDER_ERROR)
        if isinstance(value, int):
            return value
        if isinstance(value, float) and math.isfinite(value) and value.is_integer():
            return int(value)
        raise ValueError(_ORDER_ERROR)

    @field_validator("owner", mode="before")
    @classmethod
    def validate_owner(cls, value: object) -> SoftOwner:
        if not isinstance(value, str) or value not in _SOFT_OWNERS:
            raise ValueError(_OWNER_ERROR)
        return value

    @field_validator("tier", mode="before")
    @classmethod
    def validate_tier(cls, value: object) -> SoftTier | None:
        if value is None:
            return None
        if not isinstance(value, str) or value not in _SOFT_TIERS:
            raise ValueError(_TIER_ERROR)
        return value

    @field_validator("repair", mode="before")
    @classmethod
    def validate_repair(cls, value: object) -> RepairKind:
        if not isinstance(value, str) or value not in _REPAIR_KINDS:
            raise ValueError(_REPAIR_ERROR)
        return value

    @field_validator("examples", mode="before")
    @classmethod
    def validate_examples(cls, value: object) -> object:
        if not isinstance(value, list):
            raise ValueError(_EXAMPLES_ERROR)
        return value

    @field_validator("aliases", mode="before")
    @classmethod
    def validate_aliases(cls, value: object) -> object:
        if not isinstance(value, dict) or any(
            not isinstance(key, str)
            or not isinstance(aliases, list)
            or any(not isinstance(alias, str) for alias in aliases)
            for key, aliases in value.items()
        ):
            raise ValueError(_ALIASES_ERROR)
        return value


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
    ``x-softschema`` block in the compiled JSON Schema.

    Empty optional values are omitted from the emitted metadata so the compiled
    schema stays minimal.
    """
    meta = SoftFieldMeta(
        group=group,
        order=order,
        tier=tier,
        owner=owner,
        instruction=instruction,
        examples=[] if examples is None else examples,
        aliases={} if aliases is None else aliases,
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
