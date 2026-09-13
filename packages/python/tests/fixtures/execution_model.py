"""Semantic invariant absent from the CLI fixture's structural schema."""

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class Sample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str

    @model_validator(mode="after")
    def accept_name(self) -> Self:
        if self.name == "rejected":
            raise ValueError("name is unavailable")
        return self
