"""Tests for the ``status: enforced`` strict-extras overlay (apply_enforced_extras)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from softschema import apply_enforced_extras
from softschema.canonicalize import (
    ENFORCEMENT_UNSUPPORTED_MESSAGE,
    EnforcementUnsupportedError,
)
from softschema.validate import validate_structural
from tests.yaml_fixtures import load_yaml_fixture

VECTORS_PATH = (
    Path(__file__).resolve().parents[3] / "tests/parity/canonicalization-enforcement.yaml"
)


def _base_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "meta": {
                "type": "object",
                "properties": {"source": {"type": "string"}},
            },
            "scores": {"type": "object"},
            "primary": {"$ref": "#/$defs/Address"},
            "secondary": {
                "anyOf": [{"$ref": "#/$defs/Address"}, {"type": "null"}],
            },
        },
        "$defs": {
            "Address": {
                "type": "object",
                "properties": {"street": {"type": "string"}},
            }
        },
    }


def test_injects_closed_objects_where_properties_present() -> None:
    out = apply_enforced_extras(_base_schema())

    assert out["additionalProperties"] is False
    assert out["properties"]["meta"]["additionalProperties"] is False
    assert out["properties"]["primary"]["unevaluatedProperties"] is False
    assert out["properties"]["secondary"]["unevaluatedProperties"] is False
    assert "additionalProperties" not in out["$defs"]["Address"]


def test_free_form_objects_without_properties_are_untouched() -> None:
    out = apply_enforced_extras(_base_schema())

    # `scores` is a free-form mapping (no `properties`): stays open.
    assert "additionalProperties" not in out["properties"]["scores"]


def test_explicit_additional_properties_always_wins() -> None:
    schema = _base_schema()
    schema["additionalProperties"] = True
    schema["properties"]["meta"]["additionalProperties"] = {"type": "string"}

    out = apply_enforced_extras(schema)

    assert out["additionalProperties"] is True
    assert out["properties"]["meta"]["additionalProperties"] == {"type": "string"}


def test_closes_anyof_at_the_shared_evaluation_boundary() -> None:
    schema = {
        "anyOf": [
            {"type": "object", "properties": {"a": {"type": "string"}}},
            {"type": "null"},
        ]
    }

    out = apply_enforced_extras(schema)

    assert "additionalProperties" not in out["anyOf"][0]
    assert out["unevaluatedProperties"] is False


def test_property_named_properties_is_not_treated_as_keyword() -> None:
    # A field literally named "properties" inside a properties map is a name,
    # not the JSON Schema keyword; its subschema gets the overlay, but a plain
    # string-typed field named "additionalProperties" must not confuse the walk.
    schema = {
        "type": "object",
        "properties": {
            "properties": {"type": "object", "properties": {"x": {"type": "integer"}}},
        },
    }

    out = apply_enforced_extras(schema)

    assert out["additionalProperties"] is False
    assert out["properties"]["properties"]["additionalProperties"] is False


def test_input_schema_is_not_mutated() -> None:
    schema = _base_schema()
    snapshot = copy.deepcopy(schema)

    apply_enforced_extras(schema)

    assert schema == snapshot


def test_shared_enforcement_vectors() -> None:
    vectors = load_yaml_fixture(VECTORS_PATH)["enforcement"]
    for case in vectors:
        assert apply_enforced_extras(case["input"]) == case["expected"], case["id"]


def test_shared_unsupported_enforcement_vectors() -> None:
    vectors = load_yaml_fixture(VECTORS_PATH)["enforcement_unsupported"]
    for case in vectors:
        with pytest.raises(EnforcementUnsupportedError) as raised:
            apply_enforced_extras(case["input"])
        assert raised.value.schema_path == case["schema_path"], case["id"]
        assert str(raised.value) == ENFORCEMENT_UNSUPPORTED_MESSAGE


def test_shared_enforcement_validation_vectors() -> None:
    vectors = load_yaml_fixture(VECTORS_PATH)
    schemas = {case["id"]: case["input"] for case in vectors["enforcement"]}
    for case in vectors["enforcement_validation"]:
        validator = Draft202012Validator(apply_enforced_extras(schemas[case["enforcement_id"]]))
        assert all(validator.is_valid(value) for value in case["valid"]), case["enforcement_id"]
        assert not any(validator.is_valid(value) for value in case["invalid"]), case[
            "enforcement_id"
        ]


def test_reference_failure_precedes_enforcement_support_check(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(
        json.dumps({"$ref": "https://example.com/missing.schema.json"}),
        encoding="utf-8",
    )

    result = validate_structural({}, schema_path, strict_extras=True)

    assert result.errors[0]["kind"] == "schema_invalid"
    assert result.errors[0]["reason"] == "reference"


def test_available_external_reference_returns_enforcement_unsupported(tmp_path: Path) -> None:
    uri = "https://example.com/external.schema.json"
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps({"$ref": uri}), encoding="utf-8")

    result = validate_structural(
        {},
        schema_path,
        strict_extras=True,
        resources={uri: {"$id": uri, "type": "object", "properties": {"name": {"type": "string"}}}},
    )

    assert result.errors == [
        {
            "kind": "enforcement_unsupported",
            "message": ENFORCEMENT_UNSUPPORTED_MESSAGE,
            "schema_path": "/$ref",
        }
    ]
