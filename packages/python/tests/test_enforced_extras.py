"""Tests for the ``status: enforced`` strict-extras overlay (apply_enforced_extras)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from softschema import apply_enforced_extras, validate_structural
from softschema.canonicalize import EnforcementUnsupportedError

HARDENING_VECTORS = Path(__file__).resolve().parents[3] / "tests/vectors/hardening.yaml"


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
    assert out["$defs"]["Address"]["additionalProperties"] is False


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


def test_recurses_into_anyof_branches() -> None:
    schema = {
        "anyOf": [
            {"type": "object", "properties": {"a": {"type": "string"}}},
            {"type": "null"},
        ]
    }

    out = apply_enforced_extras(schema)

    assert out["anyOf"][0]["additionalProperties"] is False
    # The whole-schema node has no `properties`, so nothing is injected at the root.
    assert "additionalProperties" not in out


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
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    for case in vectors["enforcement"]:
        if case["supported"]:
            assert apply_enforced_extras(case["schema"])["additionalProperties"] is False
        else:
            try:
                apply_enforced_extras(case["schema"])
            except EnforcementUnsupportedError:
                continue
            raise AssertionError(case["id"])


def test_structural_validation_reports_unsupported_enforcement(tmp_path: Path) -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    case = next(item for item in vectors["enforcement"] if not item["supported"])
    schema_path = tmp_path / "composed.schema.yaml"
    YAML().dump(case["schema"], schema_path)
    result = validate_structural(
        {"first": "Ada", "last": "Lovelace"}, schema_path, strict_extras=True
    )
    assert result.errors[0]["kind"] == "enforcement_unsupported"
