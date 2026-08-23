"""Tests for the ``status: enforced`` strict-extras overlay (apply_enforced_extras)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from softschema import validate_structural
from softschema.canonicalize import apply_enforced_extras

HARDENING_VECTORS = Path(__file__).resolve().parents[3] / "tests/vectors/hardening.yaml"

_CLOSURE_KEYWORDS = ("additionalProperties", "unevaluatedProperties")


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
    assert not [key for key in _CLOSURE_KEYWORDS if key in out["$defs"]["Address"]]


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


def test_closes_over_anyof_without_changing_its_branches() -> None:
    schema = {
        "anyOf": [
            {"type": "object", "properties": {"a": {"type": "string"}}},
            {"type": "null"},
        ]
    }

    out = apply_enforced_extras(schema)

    assert out["unevaluatedProperties"] is False
    assert not [key for key in _CLOSURE_KEYWORDS if key in out["anyOf"][0]]


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


def test_fragments_are_never_closed_internally() -> None:
    # Closing a fragment is the failure this rule exists to prevent: an `allOf` branch
    # would reject keys its sibling declares, and an `if` matcher would stop firing.
    schema = {
        "type": "object",
        "properties": {"kind": {"type": "string"}},
        "allOf": [{"properties": {"first": {"type": "string"}}}],
        "if": {"properties": {"kind": {"const": "special"}}},
        "then": {"properties": {"extra": {"type": "string"}}},
    }

    out = apply_enforced_extras(schema)

    assert out["unevaluatedProperties"] is False
    for fragment in (out["allOf"][0], out["if"], out["then"]):
        assert "additionalProperties" not in fragment
        assert "unevaluatedProperties" not in fragment


def test_definition_reached_only_through_a_fragment_stays_open() -> None:
    # The `allOf: [{$ref: Base}, {properties: ...}]` extension idiom. Closing Base
    # lexically rejects `extra`, which the sibling branch declares.
    schema = {
        "allOf": [
            {"$ref": "#/$defs/Address"},
            {"properties": {"extra": {"type": "string"}}},
        ],
        "$defs": {"Address": {"type": "object", "properties": {"street": {"type": "string"}}}},
    }

    out = apply_enforced_extras(schema)

    assert "additionalProperties" not in out["$defs"]["Address"]
    assert "unevaluatedProperties" not in out["$defs"]["Address"]
    # The root closes over the definition instead; annotations make that correct.
    assert out["unevaluatedProperties"] is False


def test_definition_reached_from_multiple_sites_stays_reusable() -> None:
    schema = {
        "type": "object",
        "properties": {"addr": {"$ref": "#/$defs/Address"}},
        "allOf": [{"$ref": "#/$defs/Address"}],
        "$defs": {"Address": {"type": "object", "properties": {"street": {"type": "string"}}}},
    }

    out = apply_enforced_extras(schema)

    assert not [key for key in _CLOSURE_KEYWORDS if key in out["$defs"]["Address"]]
    assert out["properties"]["addr"]["unevaluatedProperties"] is False


def test_fragment_ref_to_a_free_form_definition_does_not_close_the_root() -> None:
    # Treating any `$ref` as a declaration would close this schema against every key.
    schema = {"allOf": [{"$ref": "#/$defs/Anything"}], "$defs": {"Anything": {"type": "object"}}}

    out = apply_enforced_extras(schema)

    assert "additionalProperties" not in out
    assert "unevaluatedProperties" not in out


def test_cyclic_local_references_terminate() -> None:
    schema = {
        "allOf": [{"$ref": "#/$defs/A"}],
        "$defs": {"A": {"$ref": "#/$defs/B"}, "B": {"$ref": "#/$defs/A"}},
    }

    apply_enforced_extras(schema)


def test_properties_under_not_are_prohibitions_not_declarations() -> None:
    # `not` contributes no annotations, so closing over its properties would leave the
    # schema admitting nothing at all.
    schema = {"type": "object", "not": {"properties": {"b": {"type": "string"}}, "required": ["b"]}}

    out = apply_enforced_extras(schema)

    assert "additionalProperties" not in out
    assert "unevaluatedProperties" not in out


def test_explicit_unevaluated_properties_wins() -> None:
    schema = {
        "properties": {"a": {"type": "string"}},
        "allOf": [{"properties": {"b": {"type": "string"}}}],
        "unevaluatedProperties": True,
    }

    assert apply_enforced_extras(schema)["unevaluatedProperties"] is True


def test_shared_enforcement_vectors() -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    for case in vectors["enforcement"]:
        out = apply_enforced_extras(case["schema"])
        injected = [key for key in _CLOSURE_KEYWORDS if key in out]
        expected = case["closure"]
        if expected == "none":
            assert injected == [], case["id"]
        else:
            assert injected == [expected], case["id"]
        for name, keyword in (case.get("defs_closure") or {}).items():
            definition = out["$defs"][name]
            if keyword == "none":
                assert not [key for key in _CLOSURE_KEYWORDS if key in definition], (
                    f"{case['id']}/{name}"
                )
            else:
                assert definition[keyword] is False, f"{case['id']}/{name}"


def test_composed_schemas_validate_instead_of_refusing(tmp_path: Path) -> None:
    # The shape the refusal was built for. Every document below was `invalid` with an
    # `enforcement_unsupported` record before the applicator split.
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    case = next(item for item in vectors["enforcement"] if item["id"] == "composed_object")
    schema_path = tmp_path / "composed.schema.yaml"
    YAML().dump(case["schema"], schema_path)

    ok = validate_structural({"first": "Ada", "last": "Lovelace"}, schema_path, strict_extras=True)
    assert ok.ok, ok.errors

    rejected = validate_structural(
        {"first": "Ada", "last": "Lovelace", "bogus": 1}, schema_path, strict_extras=True
    )
    assert not rejected.ok
    assert [error["code"] for error in rejected.errors] == ["undeclared_property"]
    assert rejected.errors[0]["validator"] == "unevaluatedProperties"


def test_conditional_reports_the_real_violation(tmp_path: Path) -> None:
    # Issue #41 case (b): the conditional must fire and name the missing property,
    # rather than being masked by a generic message about `allOf`.
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    case = next(item for item in vectors["enforcement"] if item["id"] == "conditional_object")
    schema_path = tmp_path / "conditional.schema.yaml"
    YAML().dump(case["schema"], schema_path)

    assert validate_structural({"kind": "plain"}, schema_path, strict_extras=True).ok

    violation = validate_structural({"kind": "special"}, schema_path, strict_extras=True)
    assert not violation.ok
    assert [error["code"] for error in violation.errors] == ["missing_property"]
    assert violation.errors[0]["property"] == "extra"
    assert violation.errors[0]["message"] == "required property 'extra' is missing"


def test_documented_engine_deviations(tmp_path: Path) -> None:
    # Each runtime asserts its own listed record set exactly, so a documented deviation
    # passes while drift on either side fails. See the section comment in the vectors.
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    for case in vectors["engine_deviations"]:
        schema_path = tmp_path / f"{case['id']}.schema.yaml"
        YAML().dump(case["schema"], schema_path)
        result = validate_structural(
            case["value"], schema_path, strict_extras=case["strict_extras"]
        )
        assert result.ok is (case["verdict"] == "valid"), case["id"]
        actual = [
            {"code": error["code"], "validator": error["validator"], "path": error["path"]}
            for error in result.errors
        ]
        assert actual == case["python"], case["id"]


def test_shared_enforcement_semantics(tmp_path: Path) -> None:
    # Raw-versus-enforced verdicts are the primary oracle: enforcement may narrow only
    # around unevaluated properties and must fail explicitly when the checked profile
    # cannot prove a safe placement.
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    for case in vectors["enforcement_semantics"]:
        schema_path = tmp_path / f"{case['id']}.schema.yaml"
        YAML().dump(case["schema"], schema_path)
        resources = case.get("resources")
        if case["raw"] != "skip":
            raw = validate_structural(case["value"], schema_path, resources=resources)
            assert raw.ok is (case["raw"] == "valid"), (case["id"], raw.errors)

        enforced = validate_structural(
            case["value"], schema_path, strict_extras=True, resources=resources
        )
        expected = case["enforced"]
        if expected == "unsupported":
            assert not enforced.ok, case["id"]
            assert enforced.errors[0]["kind"] == "enforcement_unsupported", case["id"]
            assert enforced.errors[0]["reason"] == case["reason"], case["id"]
        else:
            assert enforced.ok is (expected == "valid"), (case["id"], enforced.errors)
        if "kind" in case:
            assert enforced.errors[0]["kind"] == case["kind"], case["id"]
        if "reason" in case and expected != "unsupported":
            assert enforced.errors[0]["reason"] == case["reason"], case["id"]
        if "properties" in case:
            actual = sorted(
                error["property"]
                for error in enforced.errors
                if error.get("code") == "undeclared_property"
            )
            assert actual == case["properties"], case["id"]


def test_multiple_undeclared_keys_preserve_field_identity(tmp_path: Path) -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    case = next(item for item in vectors["enforcement"] if item["id"] == "composed_object")
    schema_path = tmp_path / "composed.schema.yaml"
    YAML().dump(case["schema"], schema_path)

    result = validate_structural(
        {"first": "Ada", "last": "Lovelace", "bogus": 1, "other": 2},
        schema_path,
        strict_extras=True,
    )

    assert [error["code"] for error in result.errors] == [
        "undeclared_property",
        "undeclared_property",
    ]
    assert [error["property"] for error in result.errors] == ["bogus", "other"]
