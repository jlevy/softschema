"""Generated-section parser, renderer, and drift-detection tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from softschema import regenerate
from softschema.generate import parse_sections

REPO_ROOT = Path(__file__).resolve().parents[3]
MOVIE_SCHEMA = REPO_ROOT / "examples/movie_page/movie-page.schema.yaml"
MOVIE_README = REPO_ROOT / "examples/movie_page/README.md"


def _doc(markers: str) -> str:
    return f"# Heading\n\nIntro text.\n\n{markers}\n\nMore text.\n"


def test_parse_sections_finds_single_block() -> None:
    text = _doc(
        '<!-- softschema:generated kind="enum_table" contract="x.yaml" -->\n'
        "old body\n"
        "<!-- /softschema:generated -->"
    )
    sections = parse_sections(text)
    assert len(sections) == 1
    assert sections[0].kind == "enum_table"
    assert sections[0].contract == "x.yaml"
    assert "old body" in sections[0].existing_content


def test_parse_sections_handles_multiple_blocks() -> None:
    text = (
        '<!-- softschema:generated kind="enum_table" contract="a.yaml" -->\n'
        "a\n<!-- /softschema:generated -->\n\n"
        '<!-- softschema:generated kind="field_list" contract="b.yaml" -->\n'
        "b\n<!-- /softschema:generated -->\n"
    )
    sections = parse_sections(text)
    assert [s.kind for s in sections] == ["enum_table", "field_list"]


def test_parse_sections_raises_on_unterminated_marker() -> None:
    text = '<!-- softschema:generated kind="enum_table" contract="a.yaml" -->\nbody only\n'
    with pytest.raises(ValueError, match="unterminated"):
        parse_sections(text)


def test_regenerate_enum_table_on_movie_readme_is_deterministic(tmp_path: Path) -> None:
    """Re-running regenerate twice produces the same content."""
    target = tmp_path / "README.md"
    target.write_text(MOVIE_README.read_text(encoding="utf-8"), encoding="utf-8")
    # Make the schema discoverable relative to the moved README.
    (tmp_path / "movie-page.schema.yaml").write_text(
        MOVIE_SCHEMA.read_text(encoding="utf-8"), encoding="utf-8"
    )

    first = regenerate(target)
    second = regenerate(target)
    assert first.sections == 1
    assert second.drift is False, "second pass should report no drift"


def test_regenerate_detects_and_repairs_drift(tmp_path: Path) -> None:
    """Stale content in the marker is fixed by `regenerate` and flagged by `--check`."""
    schema_dest = tmp_path / "movie-page.schema.yaml"
    schema_dest.write_text(MOVIE_SCHEMA.read_text(encoding="utf-8"), encoding="utf-8")
    target = tmp_path / "doc.md"
    target.write_text(
        '<!-- softschema:generated kind="enum_table" contract="movie-page.schema.yaml" -->\n'
        "stale junk that does not match the schema\n"
        "<!-- /softschema:generated -->\n",
        encoding="utf-8",
    )

    check = regenerate(target, check=True)
    assert check.drift is True
    assert check.drift_details
    # The check pass must not modify the file.
    assert "stale junk" in target.read_text(encoding="utf-8")

    fix = regenerate(target)
    assert fix.drift is True  # drift was present before the write
    # After the fix, a re-check reports no drift.
    re_check = regenerate(target, check=True)
    assert re_check.drift is False
    # MPAA enum from the schema landed in the rendered section.
    assert "PG-13" in target.read_text(encoding="utf-8")


def test_regenerate_rejects_unknown_kind(tmp_path: Path) -> None:
    schema_dest = tmp_path / "x.schema.yaml"
    schema_dest.write_text(MOVIE_SCHEMA.read_text(encoding="utf-8"), encoding="utf-8")
    target = tmp_path / "doc.md"
    target.write_text(
        '<!-- softschema:generated kind="unsupported_kind" contract="x.schema.yaml" -->\n'
        "<!-- /softschema:generated -->\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown softschema:generated kind"):
        regenerate(target)


def test_regenerate_field_list_renders_one_bullet_per_field(tmp_path: Path) -> None:
    schema_dest = tmp_path / "x.schema.yaml"
    schema_dest.write_text(MOVIE_SCHEMA.read_text(encoding="utf-8"), encoding="utf-8")
    target = tmp_path / "doc.md"
    target.write_text(
        '<!-- softschema:generated kind="field_list" contract="x.schema.yaml" -->\n'
        "<!-- /softschema:generated -->\n",
        encoding="utf-8",
    )
    regenerate(target)
    rendered = target.read_text(encoding="utf-8")
    assert "`title`" in rendered
    assert "`mpaa_rating`" in rendered
    assert "`cast`" in rendered


def test_regenerate_vocab_requires_pointer(tmp_path: Path) -> None:
    schema_dest = tmp_path / "x.schema.yaml"
    schema_dest.write_text(MOVIE_SCHEMA.read_text(encoding="utf-8"), encoding="utf-8")
    target = tmp_path / "doc.md"
    target.write_text(
        '<!-- softschema:generated kind="vocab" contract="x.schema.yaml" -->\n'
        "<!-- /softschema:generated -->\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="requires a 'pointer'"):
        regenerate(target)


def test_regenerate_vocab_renders_enum_values(tmp_path: Path) -> None:
    schema_dest = tmp_path / "x.schema.yaml"
    schema_dest.write_text(MOVIE_SCHEMA.read_text(encoding="utf-8"), encoding="utf-8")
    target = tmp_path / "doc.md"
    target.write_text(
        '<!-- softschema:generated kind="vocab" contract="x.schema.yaml" '
        'pointer="/properties/mpaa_rating" -->\n'
        "<!-- /softschema:generated -->\n",
        encoding="utf-8",
    )
    regenerate(target)
    rendered = target.read_text(encoding="utf-8")
    for value in ("`G`", "`PG`", "`PG-13`", "`R`", "`NC-17`", "`NR`"):
        assert value in rendered


def test_movie_example_marker_is_in_sync_with_committed_schema() -> None:
    """The example README marker must not drift; CI's contract test."""
    result = regenerate(MOVIE_README, check=True)
    assert result.drift is False, result.drift_details
