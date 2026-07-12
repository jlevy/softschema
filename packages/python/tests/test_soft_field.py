"""SoftField round-trip tests: Pydantic annotation → compiled JSON Schema."""

from __future__ import annotations

from pathlib import Path

from frontmatter_format import read_yaml_file
from pydantic import BaseModel, ConfigDict, ValidationError
from ruamel.yaml import YAML

from softschema import SoftField, compile_model
from softschema.soft_field import SoftFieldMeta

HARDENING_VECTORS = Path(__file__).resolve().parents[3] / "tests/vectors/hardening.yaml"


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

    schema = read_yaml_file(out)
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
    """Defaults (empty examples/aliases, repair=none) stay out of the compiled schema."""
    out = tmp_path / "minimal.schema.yaml"
    compile_model(_AnnotatedModel, out, contract_id="example:Annotated/v1")
    schema = read_yaml_file(out)

    for prop in schema["properties"].values():
        meta = prop.get("x-softschema", {})
        assert "examples" not in meta
        assert "aliases" not in meta
        assert "repair" not in meta


def test_soft_field_movie_example_genres_block_present() -> None:
    """The movie example annotates `genres`; the committed compiled schema must show it."""
    repo_root = Path(__file__).resolve().parents[3]
    schema_path = repo_root / "examples/movie_page/movie-page.schema.yaml"
    schema = read_yaml_file(schema_path)
    genres_meta = schema["properties"]["genres"].get("x-softschema")

    assert genres_meta is not None
    assert genres_meta["group"] == "taxonomy"
    assert genres_meta["tier"] == "constrained"
    assert genres_meta["owner"] == "agent"
    assert "IMDb" in genres_meta["instruction"]


def test_shared_annotation_vectors() -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    for case in vectors["compiler_annotations"]:
        if "metadata" not in case:
            continue
        metadata = dict(case["metadata"])
        metadata.pop("description", None)
        if case["valid"]:
            assert SoftFieldMeta.model_validate(metadata).group == "identity"
        else:
            try:
                SoftFieldMeta.model_validate(metadata)
            except ValidationError:
                continue
            raise AssertionError(case["id"])
