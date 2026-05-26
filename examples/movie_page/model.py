"""Pydantic model for the movie page example."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from softschema import SField

MpaaRating = Literal["G", "PG", "PG-13", "R", "NC-17", "NR"]


class CastMember(BaseModel):
    """One billed cast member."""

    model_config = ConfigDict(extra="forbid")

    actor: str
    character: str


class RottenTomatoesRating(BaseModel):
    """Rotten Tomatoes critic and audience scores."""

    model_config = ConfigDict(extra="forbid")

    critics_percent: int = Field(ge=0, le=100, description="Tomatometer score, 0-100.")
    audience_percent: int = Field(ge=0, le=100, description="Popcornmeter score, 0-100.")
    critic_review_count: int = Field(ge=0)


class ImdbRating(BaseModel):
    """IMDb aggregate rating."""

    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=10.0, description="IMDb rating on a 0-10 scale.")
    total_votes: int = Field(ge=0)


class MovieRatings(BaseModel):
    """Aggregate ratings from external sources."""

    model_config = ConfigDict(extra="forbid")

    rotten_tomatoes: RottenTomatoesRating | None = None
    imdb: ImdbRating | None = None


class MoviePage(BaseModel):
    """A small movie info page, similar to a public IMDB-style listing.

    The fields illustrate the structural variety a softschema artifact can carry:
    constrained scalars, enums, lists of strings, lists of structured records, and
    optional nested objects.
    """

    model_config = ConfigDict(extra="forbid")

    title: str
    release_year: int = Field(ge=1888)
    runtime_minutes: int = Field(gt=0)
    mpaa_rating: MpaaRating | None = None
    directors: list[str] = Field(min_length=1)
    genres: list[str] = SField(
        description="Genre labels for the film.",
        group="taxonomy",
        owner="agent",
        tier="constrained",
        instruction="Pick from the standard IMDb genre vocabulary; at least one.",
        min_length=1,
    )
    tagline: str | None = None
    synopsis: str
    cast: list[CastMember] = Field(default_factory=list)
    ratings: MovieRatings
