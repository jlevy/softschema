from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from softschema import compile_model, validate_structural
from softschema.errors import canonical_number, render_structural_message, structural_error_record


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


def test_canonical_number_drops_trailing_fraction() -> None:
    # ss-wbnm: a whole-valued float renders in canonical (int) form so it is
    # byte-identical to the TypeScript impl, which has no float/int distinction.
    assert canonical_number(2.0) == 2
    assert isinstance(canonical_number(2.0), int)
    assert canonical_number(-2.0) == -2
    assert canonical_number(0.0) == 0
    # Whole floats below 1e21 become canonical ints (the range where JS renders a
    # whole-valued number as a plain integer via String()/JSON.stringify()).
    assert canonical_number(1e15) == 1000000000000000
    assert isinstance(canonical_number(1e15), int)
    assert canonical_number(1e16) == 10000000000000000  # the reviewer's divergence case
    assert isinstance(canonical_number(1e16), int)
    assert canonical_number(1e20) == 100000000000000000000
    # Non-whole floats keep their fraction; ints and bools are untouched.
    assert canonical_number(0.3) == 0.3
    assert canonical_number(7) == 7
    assert canonical_number(True) is True
    # Floats at/beyond 1e21 keep exponential repr (matches the TS formatter and JS String).
    assert canonical_number(1e21) == 1e21
    assert isinstance(canonical_number(1e21), float)
    assert repr(canonical_number(1e21)) == "1e+21"


def test_whole_float_renders_canonically_in_messages_and_records() -> None:
    # The bound 2.0 and the offending 1.0 both render without a trailing `.0`.
    assert render_structural_message("minimum", 2.0, 1.0) == "value 1 is less than the minimum of 2"
    assert render_structural_message("enum", [1.0, 2.0], 3.0) == "value 3 is not one of [1, 2]"
    record = structural_error_record(
        path=["ratio"], validator="minimum", validator_value=2.0, value=1.0
    )
    # Stored fields are canonicalized too, so they match the message and the TS record.
    assert record["value"] == 1
    assert record["validator_value"] == 2
    assert record["message"] == "value 1 is less than the minimum of 2"


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
