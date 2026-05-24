"""Example host integration for validating movie page artifacts."""

from __future__ import annotations

from pathlib import Path

from examples.movie_page.model import MoviePage
from softschema import (
    ArtifactValidationResult,
    SchemaBinding,
    SchemaRegistry,
    Status,
    validate_artifact,
)

MOVIE_PAGE_CONTRACT_ID = "example.movies:MoviePage/v1"
MOVIE_SCHEMA_PATH = Path(__file__).with_name("movie-page.schema.yaml")


def build_movie_page_registry() -> SchemaRegistry:
    """Register the complete bindings a host application owns."""
    registry = SchemaRegistry()
    registry.register(
        SchemaBinding(
            contract_id=MOVIE_PAGE_CONTRACT_ID,
            model=MoviePage,
            envelope_key="movie",
            status=Status.enforced,
            schema_path=MOVIE_SCHEMA_PATH,
        )
    )
    return registry


def validate_movie_page(path: Path) -> ArtifactValidationResult:
    """Validate a movie page at the host application's file boundary."""
    return validate_artifact(
        path,
        contract_id=MOVIE_PAGE_CONTRACT_ID,
        registry=build_movie_page_registry(),
    )
