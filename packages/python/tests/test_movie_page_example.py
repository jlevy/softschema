from __future__ import annotations

import json
from pathlib import Path

from frontmatter_format import fmf_read

from examples.movie_page.host_integration import validate_movie_page
from softschema.cli import main as softschema_main

ROOT = Path(__file__).resolve().parents[3]
MOVIE_PAGE = ROOT / "examples/movie_page/spirited-away.md"
MOVIE_SCHEMA = ROOT / "examples/movie_page/movie-page.schema.yaml"


def test_movie_page_demo_matches_structured_values() -> None:
    result = validate_movie_page(MOVIE_PAGE)

    assert result.ok
    assert result.values is not None
    assert result.values == {
        "title": "Spirited Away",
        "release_year": 2001,
        "runtime_minutes": 125,
        "mpaa_rating": "PG",
        "directors": ["Hayao Miyazaki"],
        "genres": ["Animation", "Adventure", "Family"],
        "synopsis": (
            "Ten-year-old Chihiro and her parents stumble into a mysterious abandoned "
            "town that turns out to be a spirit world. After her parents are transformed "
            "into pigs, Chihiro must take a job in a magical bathhouse run by the witch "
            "Yubaba and find a way to break the spell so the family can return home.\n"
        ),
        "cast": [
            {"actor": "Rumi Hiiragi", "character": "Chihiro / Sen"},
            {"actor": "Miyu Irino", "character": "Haku"},
            {"actor": "Mari Natsuki", "character": "Yubaba"},
        ],
        "ratings": {
            "rotten_tomatoes": {
                "critics_percent": 96,
                "audience_percent": 96,
                "critic_review_count": 225,
            },
            "imdb": {
                "score": 8.6,
                "total_votes": 850000,
            },
        },
    }

    body, _frontmatter = fmf_read(MOVIE_PAGE)
    movie = result.values
    rt = movie["ratings"]["rotten_tomatoes"]
    imdb = movie["ratings"]["imdb"]

    assert f"# {movie['title']} ({movie['release_year']})" in body
    assert "Hayao Miyazaki" in body
    assert ", ".join(movie["genres"]) in body
    assert f"{rt['critics_percent']}% Tomatometer" in body
    assert f"{rt['critic_review_count']} critic reviews" in body
    assert f"{rt['audience_percent']}% Popcornmeter" in body
    assert f"{imdb['score']} out of 10" in body
    assert "Rumi Hiiragi" in body
    assert "| MPAA rating | PG |" in body


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
    assert output["values"]["mpaa_rating"] == "PG"
    assert output["values"]["ratings"]["rotten_tomatoes"] == {
        "critics_percent": 96,
        "audience_percent": 96,
        "critic_review_count": 225,
    }
    assert output["values"]["ratings"]["imdb"]["score"] == 8.6
