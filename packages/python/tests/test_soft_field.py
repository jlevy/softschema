"""SoftField round-trip tests: Pydantic annotation → JSON Schema sidecar."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from softschema import SoftField, compile_model


def _read_yaml(path: Path) -> dict:
    from frontmatter_format import read_yaml_file

    return read_yaml_file(path)


class _AnnotatedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = SoftField(
        description="Display title.",
        group="identity",
        owner="agent",
        tier="hard_fact",
    )
    summary: str = SoftField(
        description="One-sentence summary.",
        group="narrative",
        owner="postprocess",
        tier="narrative",
        instruction="Keep under 200 chars.",
    )
    score: int = SoftField(
        description="Score 0-100.",
        group="metrics",
        owner="system",
        tier="constrained",
        ge=0,
        le=100,
    )


def test_soft_field_propagates_x_softschema_into_compiled_schema(tmp_path: Path) -> None:
    out = tmp_path / "annotated.schema.yaml"
    compile_model(_AnnotatedModel, out, contract_id="example:Annotated/v1")

    schema = _read_yaml(out)
    props = schema["properties"]

    assert props["title"]["x-softschema"] == {
        "group": "identity",
        "owner": "agent",
        "tier": "hard_fact",
    }
    assert props["summary"]["x-softschema"] == {
        "group": "narrative",
        "instruction": "Keep under 200 chars.",
        "owner": "postprocess",
        "tier": "narrative",
    }
    assert props["score"]["x-softschema"] == {
        "group": "metrics",
        "owner": "system",
        "tier": "constrained",
    }
    # Field constraints (ge/le) flow through the standard Pydantic path.
    assert props["score"]["minimum"] == 0
    assert props["score"]["maximum"] == 100


def test_soft_field_omits_empty_optional_metadata(tmp_path: Path) -> None:
    """Defaults (empty examples/aliases, repair=none) stay out of the sidecar."""
    out = tmp_path / "minimal.schema.yaml"
    compile_model(_AnnotatedModel, out, contract_id="example:Annotated/v1")
    schema = _read_yaml(out)

    for prop in schema["properties"].values():
        meta = prop.get("x-softschema", {})
        assert "examples" not in meta
        assert "aliases" not in meta
        assert "repair" not in meta


def test_soft_field_movie_example_genres_block_present() -> None:
    """The movie example annotates `genres`; the committed sidecar must show it."""
    repo_root = Path(__file__).resolve().parents[3]
    schema_path = repo_root / "examples/movie_page/movie-page.schema.yaml"
    schema = _read_yaml(schema_path)
    genres_meta = schema["properties"]["genres"].get("x-softschema")

    assert genres_meta is not None
    assert genres_meta["group"] == "taxonomy"
    assert genres_meta["tier"] == "constrained"
    assert genres_meta["owner"] == "agent"
    assert "IMDb" in genres_meta["instruction"]
