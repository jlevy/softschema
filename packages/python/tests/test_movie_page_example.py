from __future__ import annotations

import json
from pathlib import Path

import pytest
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


def test_validate_cli_reads_contract_status_from_demo_yaml(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`softschema validate` reads contract and status from the document.

    The demo artifact carries a top-level `title:` alongside `movie:`, so the
    envelope cannot be inferred automatically. ``--envelope movie`` designates
    it explicitly; that is the documented escape hatch for any artifact that
    coexists with host-specific metadata softschema does not interpret.
    """
    exit_code = softschema_main(
        [
            "validate",
            str(MOVIE_PAGE),
            "--model",
            "examples.movie_page.model:MoviePage",
            "--schema",
            str(MOVIE_SCHEMA),
            "--envelope",
            "movie",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["contract_id"] == "example.movies:MoviePage/v1"
    assert output["status"] == "enforced"
    assert output["contract"]["envelope_key"] == "movie"
    assert output["values"]["mpaa_rating"] == "PG"
    assert output["values"]["ratings"]["rotten_tomatoes"] == {
        "critics_percent": 96,
        "audience_percent": 96,
        "critic_review_count": 225,
    }
    assert output["values"]["ratings"]["imdb"]["score"] == 8.6
    # `values` carries the movie payload (whose own `title` is "Spirited Away"); the
    # unrelated top-level `title:` ("Spirited Away (2001)") sits outside the envelope
    # and never reaches the validator.
    assert output["values"]["title"] == "Spirited Away"


def test_validate_cli_ignores_unrelated_top_level_keys(capsys: pytest.CaptureFixture[str]) -> None:
    """Extra top-level frontmatter keys do not cause validation to fail.

    softschema must neither forbid nor interpret keys outside the
    `softschema:` block and the designated envelope, so a `title:` alongside
    `movie:` is a no-op from the validator's perspective once the envelope is
    pointed at `movie` via ``--envelope``.
    """
    _content, frontmatter = fmf_read(MOVIE_PAGE)
    assert isinstance(frontmatter, dict)
    assert frontmatter.get("title") == "Spirited Away (2001)"
    assert "softschema" in frontmatter
    assert "movie" in frontmatter

    exit_code = softschema_main(
        [
            "validate",
            str(MOVIE_PAGE),
            "--model",
            "examples.movie_page.model:MoviePage",
            "--schema",
            str(MOVIE_SCHEMA),
            "--envelope",
            "movie",
        ]
    )
    assert exit_code == 0


def test_movie_page_validates_with_no_flags() -> None:
    """The flagship artifact is fully self-describing.

    Its metadata quartet (``contract``, ``schema``, ``envelope``, ``status``)
    binds the compiled schema and designates the payload, so a bare
    ``softschema validate <doc>`` succeeds even though the artifact also
    carries a host ``title:`` key.
    """
    exit_code = softschema_main(["validate", str(MOVIE_PAGE)])
    assert exit_code == 0


def test_validate_cli_errors_when_envelope_is_ambiguous(capsys: pytest.CaptureFixture[str]) -> None:
    """Without any designation the CLI must refuse to guess between keys.

    The spec says the envelope must be designated (flag, registry, or
    ``softschema.envelope``) when multiple non-`softschema` top-level keys
    exist; auto-detection is intentionally not extended to multi-key
    documents. The error message lists the candidates.
    """
    fixture = ROOT / "tests/golden/fixtures/multi-key-no-envelope.md"
    exit_code = softschema_main(["validate", str(fixture)])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "multiple top-level frontmatter keys" in captured.err
    assert "record" in captured.err
    assert "title" in captured.err
