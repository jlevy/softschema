"""SoftField round-trip tests: Pydantic annotation → compiled JSON Schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from frontmatter_format import read_yaml_file
from pydantic import BaseModel, ConfigDict, ValidationError

from softschema import SoftField, SoftFieldMeta, compile_model


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
        order=2,
        instruction="Keep under 200 chars.",
        examples=["A concise summary."],
        aliases={"tone": ["concise"]},
        repair="safe_coerce",
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
        "aliases": {"tone": ["concise"]},
        "examples": ["A concise summary."],
        "group": "narrative",
        "instruction": "Keep under 200 chars.",
        "order": 2,
        "owner": "postprocess",
        "repair": "safe_coerce",
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

    class MinimalAnnotatedModel(BaseModel):
        value: str = SoftField(description="Minimal value.", group="minimal")

    out = tmp_path / "minimal.schema.yaml"
    compile_model(MinimalAnnotatedModel, out, contract_id="example:Annotated/v1")
    schema = read_yaml_file(out)

    for prop in schema["properties"].values():
        meta = prop.get("x-softschema", {})
        assert "examples" not in meta
        assert "aliases" not in meta
        assert "repair" not in meta


def test_soft_field_rejects_annotations_outside_the_public_schema() -> None:
    invalid: list[tuple[dict[str, Any], str]] = [
        ({"group": ""}, "soft field annotation group must be a non-empty string"),
        (
            {"group": "valid", "instruction": ""},
            "soft field annotation instruction must be a non-empty string",
        ),
        (
            {"group": "valid", "order": 1.5},
            "soft field annotation order must be an integer",
        ),
        (
            {"group": "valid", "order": True},
            "soft field annotation order must be an integer",
        ),
        (
            {"group": "valid", "owner": "runtime"},
            "soft field annotation owner must be one of: agent, postprocess, system, human",
        ),
        (
            {"group": "valid", "tier": "approximate"},
            "soft field annotation tier must be one of: hard_fact, constrained, narrative",
        ),
        (
            {"group": "valid", "repair": "execute"},
            "soft field annotation repair must be one of: none, safe_coerce, suggest_alias",
        ),
        (
            {"group": "valid", "examples": "not-an-array"},
            "soft field annotation examples must be an array",
        ),
        (
            {"group": "valid", "aliases": {"tone": [1]}},
            "soft field annotation aliases must be an object of string arrays",
        ),
    ]

    for values, message in invalid:
        with pytest.raises(ValidationError) as meta_error:
            SoftFieldMeta.model_validate(values)
        with pytest.raises(ValidationError) as field_error:
            SoftField(description="Invalid annotation.", **values)
        for error in (meta_error.value, field_error.value):
            record = error.errors(include_url=False)[0]
            assert record["msg"] == f"Value error, {message}"
            context = record.get("ctx")
            assert context is not None
            assert str(context["error"]) == message

    assert SoftFieldMeta.model_validate({"group": "valid", "order": 2.0}).order == 2
