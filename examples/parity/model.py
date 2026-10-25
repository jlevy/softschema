"""Comprehensive cross-language parity fixture (Pydantic side).

This model is not a teaching example; it is a conformance fixture. It exercises the
portable JSON Schema type/constraint matrix that softschema guarantees compiles to the
*same canonical sidecar* from Pydantic and from the equivalent Zod schema
(`packages/typescript/test/fixtures/parity.ts`). The committed `parity.schema.yaml` is
the shared reference both implementations must reproduce byte-for-byte.

Each field is chosen to cover one portable feature; see the cross-language reconciliation
matrix in the plan spec for how Pydantic and Zod outputs are normalized to agree.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from softschema import SoftField


class Address(BaseModel):
    """A nested object, extracted to $defs and referenced by $ref."""

    model_config = ConfigDict(extra="forbid")

    street: str
    zip_code: str = Field(pattern="^[0-9]{5}$")


class Event(BaseModel):
    """A nested object referenced from more than one field (reuse → single $defs entry)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    timestamp: int = Field(ge=0)


class KitchenSink(BaseModel):
    """Every portable field shape softschema supports across Pydantic and Zod."""

    model_config = ConfigDict(extra="forbid")

    # Required scalar.
    title: str
    # Bounded integer (minimum / maximum).
    count: int = Field(ge=0, le=100)
    # Exclusive-bounded number (exclusiveMinimum / exclusiveMaximum).
    ratio: float = Field(gt=0, lt=1)
    # multipleOf.
    step: int = Field(multiple_of=5)
    # String constraints (minLength / maxLength / pattern).
    code: str = Field(min_length=2, max_length=8, pattern="^[A-Z]+$")
    # Prefix, suffix, and substring constraints are plain patterns (Zod's `.startsWith()`,
    # `.endsWith()`, and `.includes()`).
    sku: str = Field(pattern="^SKU-.*")
    filename: str = Field(pattern=r".*\.md$")
    contact: str = Field(pattern="@")
    # Boolean.
    active: bool
    # Semantic temporal strings compile to format annotations.
    calendar_date: date
    calendar_datetime: datetime
    calendar_duration: timedelta
    calendar_time: time
    # String enum (Literal).
    kind: Literal["alpha", "beta", "gamma"]
    # Non-null defaults of several types.
    priority: int = 1
    label: str = "none"
    enabled: bool = True
    # List of scalars with a minimum length.
    tags: list[str] = Field(min_length=1)
    # Optional + nullable (no default after canonicalization).
    notes: str | None = None
    # Optional + nullable with a non-null default.
    nickname: str | None = "n/a"
    # Optional enum (Literal | None).
    rank: Literal["low", "high"] | None = None
    # Text the compilers must escape: U+0085, U+2028 and U+2029 in a description, a
    # default, and an enum value. Both writers emit `\N`, `\L` and `\P`, and both readers
    # read the sidecar back; raw, the portable preflight would reject it.
    separator: Literal["next\u0085line", "line\u2028separator"] = Field(
        default="next\u0085line",
        description="Carries a next line\u0085a line\u2028and a paragraph\u2029separator.",
    )
    # Text one writer or the other once wrote in a form the other reader refused: a CRLF
    # (Python folded it in a block literal), a tab in a plain scalar and a bare `=` (the
    # yaml package wrote them plain, ruamel refused them). Both writers now quote them.
    control_text: Literal["=", "tab\there"] = Field(
        default="tab\there",
        description="Carries a CRLF\r\nand a tab\tand ends with =",
    )
    # Required nested object (single-use $ref).
    primary: Address
    # Optional nested object (anyOf [$ref, null]).
    secondary: Address | None = None
    # List of nested objects; Event is reused below, so it lands once in $defs.
    history: list[Event] = Field(default_factory=list)
    last_event: Event | None = None
    # Fixed-length tuple (prefixItems with minItems and maxItems).
    pair: tuple[str, int]
    # Mapping with typed values (additionalProperties schema).
    scores: dict[str, int] = Field(default_factory=dict)
    # Non-nullable union.
    mixed: int | str
    # Field carrying the full x-softschema annotation surface.
    channels: list[str] = SoftField(
        description="Delivery channels.",
        group="routing",
        order=1,
        tier="constrained",
        owner="agent",
        instruction="Pick from the approved channel vocabulary.",
        examples=["email", "sms"],
        aliases={"email": ["e-mail", "mail"]},
        repair="suggest_alias",
        min_length=1,
    )
