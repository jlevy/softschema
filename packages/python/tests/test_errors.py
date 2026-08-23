from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from softschema import compile_model, validate_structural
from softschema.errors import (
    canonical_number,
    render_structural_message,
    structural_error_code,
    structural_error_record,
)


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
        "code": "invalid_value",
        "path": ["count"],
        "validator": "maximum",
        "validator_value": 10,
        "value": 11,
        "message": "value 11 is greater than the maximum of 10",
    }


def test_structural_error_code_categories() -> None:
    # `code` is the documented match surface, so both closure keywords — the one a
    # simple schema reports and the one a composed schema reports — must land on the
    # same category, and share a message.
    assert structural_error_code("additionalProperties") == "undeclared_property"
    assert structural_error_code("unevaluatedProperties") == "undeclared_property"
    assert structural_error_code("required") == "missing_property"
    assert structural_error_code("enum") == "invalid_value"
    assert render_structural_message("unevaluatedProperties", False, {"a": 1}) == (
        render_structural_message("additionalProperties", False, {"a": 1})
    )


def test_unmapped_keyword_is_a_visible_signal() -> None:
    # A keyword with no template must not be folded silently into `invalid_value`;
    # `unmapped_keyword` is what makes the gap greppable.
    assert structural_error_code("someFutureKeyword") == "unmapped_keyword"


def test_validate_structural_emits_neutral_records(tmp_path: Path) -> None:
    schema_path = tmp_path / "sample.schema.yaml"
    compile_model(Sample, schema_path, contract_id="example:Sample/v1")

    result = validate_structural({"count": 99, "label": "ok"}, schema_path)

    assert not result.ok
    error = result.errors[0]
    assert error["kind"] == "schema_violation"
    assert error["validator"] == "maximum"
    assert "greater than the maximum" in error["message"]


def test_field_level_errors_preserve_property_identity(tmp_path: Path) -> None:
    schema_path = tmp_path / "fields.schema.yaml"
    schema_path.write_text(
        "type: object\nrequired: [a, b]\nproperties:\n  a: true\n  b: true\n"
        "additionalProperties: false\n"
    )

    missing = validate_structural({}, schema_path)
    extras = validate_structural({"bogus": 1, "other": 2}, schema_path)

    assert [(error["code"], error["property"]) for error in missing.errors] == [
        ("missing_property", "a"),
        ("missing_property", "b"),
    ]
    assert [(error["code"], error["property"]) for error in extras.errors] == [
        ("undeclared_property", "bogus"),
        ("undeclared_property", "other"),
        ("missing_property", "a"),
        ("missing_property", "b"),
    ]
