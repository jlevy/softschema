from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from softschema import compile_model, validate_structural
from softschema.errors import render_structural_message, structural_error_record


class Sample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int = Field(ge=0, le=10)
    label: str


def test_render_structural_message_is_engine_neutral() -> None:
    # The wording is the cross-language contract; pin a few keywords exactly.
    assert render_structural_message("minimum", 0, -1) == "value -1 is less than the minimum of 0"
    assert (
        render_structural_message("enum", ["G", "PG"], "X") == "value 'X' is not one of ['G', 'PG']"
    )
    assert render_structural_message("type", "integer", "x") == "value 'x' is not of type 'integer'"


def test_structural_error_record_shape() -> None:
    record = structural_error_record(
        path=["count"], validator="maximum", validator_value=10, value=11
    )
    assert record == {
        "kind": "schema_violation",
        "path": ["count"],
        "validator": "maximum",
        "validator_value": 10,
        "value": 11,
        "message": "value 11 is greater than the maximum of 10",
    }


def test_validate_structural_emits_neutral_records(tmp_path: Path) -> None:
    schema_path = tmp_path / "sample.schema.yaml"
    compile_model(Sample, schema_path, contract_id="example:Sample/v1")

    result = validate_structural({"count": 99, "label": "ok"}, schema_path)

    assert not result.ok
    error = result.errors[0]
    assert error["kind"] == "schema_violation"
    assert error["validator"] == "maximum"
    assert "greater than the maximum" in error["message"]
