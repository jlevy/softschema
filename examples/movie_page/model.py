"""Pydantic model for the movie page example."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RottenTomatoesCritics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = "Tomatometer"
    score_percent: int = Field(ge=0, le=100)
    total_reviews: int = Field(ge=0)


class RottenTomatoesAudience(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = "Popcornmeter"
    score_percent: int = Field(ge=0, le=100)
    total_ratings: int = Field(ge=0)
    total_ratings_display: str


class RottenTomatoesRatings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    critics: RottenTomatoesCritics
    audience: RottenTomatoesAudience


class MovieRatings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rotten_tomatoes: RottenTomatoesRatings


class MoviePage(BaseModel):
    """Movie page fields consumed from the Markdown frontmatter."""

    model_config = ConfigDict(extra="forbid")

    title: str
    release_year: int = Field(ge=1888)
    directors: list[str]
    genres: list[str] = Field(min_length=1)
    runtime_minutes: int = Field(gt=0)
    description: str
    ratings: MovieRatings
