from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

from softschema.patterns import is_portable_pattern, portable_pattern_matches
from softschema.validate import ValidationResult, validate_values

VECTORS_PATH = Path(__file__).resolve().parents[3] / "tests/parity/portable-patterns.json"


def _vectors() -> dict[str, Any]:
    return json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


def _validate(
    tmp_path: Path,
    value: Any,
    schema: dict[str, Any],
    *,
    resources: dict[str, bool | dict[str, Any]] | None = None,
) -> ValidationResult:
    path = tmp_path / "portable-pattern.schema.json"
    path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
    return validate_values(value, schema=path, resources=resources)


def test_portable_pattern_syntax_matches_shared_profile() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for case in _vectors()["syntax"]:
            assert is_portable_pattern(case["pattern"]) is case["supported"], case["id"]


def test_portable_pattern_matching_matches_shared_vectors_without_warnings() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for vector in _vectors()["matching"]:
            for case in vector["cases"]:
                assert (
                    portable_pattern_matches(vector["pattern"], case["value"]) is case["matches"]
                ), (vector["id"], case["value"])


def test_validation_uses_portable_end_dot_and_original_error_pattern(tmp_path: Path) -> None:
    end_result = _validate(tmp_path, "a\n", {"type": "string", "pattern": "^a$"})
    assert end_result.structural.ok is False

    dot_result = _validate(tmp_path, "\r", {"type": "string", "pattern": "."})
    assert dot_result.structural.errors == [
        {
            "kind": "schema_violation",
            "path": [],
            "validator": "pattern",
            "validator_value": ".",
            "value": "\r",
            "message": "value '\\r' does not match pattern '.'",
        }
    ]


def test_pattern_properties_use_portable_matching_for_evaluated_keys(tmp_path: Path) -> None:
    schema = {
        "type": "object",
        "allOf": [{"patternProperties": {"^a$": {"type": "integer"}}}],
        "unevaluatedProperties": False,
    }
    assert _validate(tmp_path, {"a": 1}, schema).structural.ok is True
    result = _validate(tmp_path, {"a\n": 1}, schema)
    assert result.structural.ok is False
    assert result.structural.errors[0]["validator"] == "unevaluatedProperties"


def test_pattern_scan_ignores_pattern_shaped_annotation_data(tmp_path: Path) -> None:
    schema = {
        "type": "object",
        "examples": [{"pattern": "["}],
        "properties": {"value": {"type": "string"}},
    }
    assert _validate(tmp_path, {"value": "ok"}, schema).structural.ok is True


def test_nested_pattern_property_error_has_stable_escaped_pointer(tmp_path: Path) -> None:
    pattern = "(?=a/a~)"
    result = _validate(
        tmp_path,
        {},
        {"type": "object", "patternProperties": {pattern: {"type": "integer"}}},
    )
    assert result.structural.errors == [
        {
            "kind": "schema_invalid",
            "reason": "pattern",
            "message": "compiled schema contains an unsupported or invalid pattern",
            "schema_path": "/patternProperties/(?=a~1a~0)",
            "pattern": pattern,
        }
    ]


def test_supplied_resource_patterns_use_the_same_profile_and_lowering(tmp_path: Path) -> None:
    resource_id = "urn:example:portable-pattern"
    result = _validate(
        tmp_path,
        "a\n",
        {"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": resource_id},
        resources={
            resource_id: {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": resource_id,
                "type": "string",
                "pattern": "^a$",
            }
        },
    )
    assert result.structural.errors[0]["validator"] == "pattern"
    assert result.structural.errors[0]["validator_value"] == "^a$"
