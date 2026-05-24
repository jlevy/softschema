from __future__ import annotations

import json
from pathlib import Path

from frontmatter_format import fmf_read

from examples.movie_page.model import MoviePage
from softschema import SchemaBinding, Status, validate_artifact
from softschema.cli import main as softschema_main

ROOT = Path(__file__).resolve().parents[3]
MOVIE_PAGE = ROOT / "examples/movie_page/spirited-away.md"
MOVIE_SCHEMA = ROOT / "examples/movie_page/movie-page.schema.yaml"


def test_movie_page_demo_matches_structured_values() -> None:
    binding = SchemaBinding(
        contract_id="example.movies:MoviePage/v1",
        model=MoviePage,
        envelope_key="movie",
        status=Status.enforced,
        schema_path=MOVIE_SCHEMA,
    )

    result = validate_artifact(MOVIE_PAGE, binding=binding)

    assert result.ok
    assert result.values is not None
    assert result.values == {
        "title": "Spirited Away",
        "release_year": 2001,
        "directors": ["Hayao Miyazaki"],
        "genres": ["Animation", "Adventure", "Family"],
        "runtime_minutes": 125,
        "description": (
            "A girl enters a spirit world and has to find a way to save her parents "
            "while working in a bathhouse for supernatural visitors.\n"
        ),
        "ratings": {
            "rotten_tomatoes": {
                "critics": {
                    "label": "Tomatometer",
                    "score_percent": 96,
                    "total_reviews": 225,
                },
                "audience": {
                    "label": "Popcornmeter",
                    "score_percent": 96,
                    "total_ratings": 250000,
                    "total_ratings_display": "250,000+",
                },
            }
        },
    }

    body, _frontmatter = fmf_read(MOVIE_PAGE)
    movie = result.values
    rt = movie["ratings"]["rotten_tomatoes"]
    critics = rt["critics"]
    audience = rt["audience"]
    normalized_body = " ".join(body.split())

    assert f"# {movie['title']} ({movie['release_year']})" in body
    assert "Hayao Miyazaki's 2001 animated adventure family film" in body
    assert (
        f"{critics['score_percent']}% {critics['label']} based on "
        f"{critics['total_reviews']} critic reviews"
    ) in normalized_body
    assert (
        f"{audience['score_percent']}% {audience['label']} based on "
        f"{audience['total_ratings_display']} audience ratings"
    ) in normalized_body
    assert "| Rotten Tomatoes Critics | 96% Tomatometer | 225 reviews |" in body
    assert "| Rotten Tomatoes Audience | 96% Popcornmeter | 250,000+ audience ratings |" in body


def test_validate_cli_reads_contract_status_and_envelope_from_demo_yaml(capsys) -> None:
    exit_code = softschema_main(
        [
            "validate",
            str(MOVIE_PAGE),
            "--model",
            "examples.movie_page.model:MoviePage",
            "--schema",
            str(MOVIE_SCHEMA),
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["contract_id"] == "example.movies:MoviePage/v1"
    assert output["status"] == "enforced"
    assert output["binding"]["envelope_key"] == "movie"
    assert output["values"]["ratings"]["rotten_tomatoes"]["critics"] == {
        "label": "Tomatometer",
        "score_percent": 96,
        "total_reviews": 225,
    }
