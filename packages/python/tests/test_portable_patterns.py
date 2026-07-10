from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

from softschema.patterns import (
    PORTABLE_PATTERN_CACHE_SIZE,
    PORTABLE_PATTERN_MAX_CODEPOINTS,
    PORTABLE_PATTERN_MAX_DFA_STATES,
    PORTABLE_PATTERN_MAX_DFA_TRANSITIONS,
    PORTABLE_PATTERN_MAX_GROUP_DEPTH,
    PORTABLE_PATTERN_MAX_NFA_STATES,
    PORTABLE_PATTERN_MAX_SCHEMA_CODEPOINTS,
    PORTABLE_PATTERN_MAX_SCHEMA_PATTERNS,
    PORTABLE_PATTERN_MAX_VALIDATION_WORK,
    _portable_pattern_cache_membership_info,
    is_portable_pattern,
    portable_pattern_cache_info,
    portable_pattern_matches,
    portable_pattern_validation_budget,
)
from softschema.validate import (
    ValidationResult,
    structural_error_offending_property,
    validate_values,
)

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
    profile = _vectors()["profile"]
    assert profile["max_pattern_codepoints"] == PORTABLE_PATTERN_MAX_CODEPOINTS
    assert profile["max_group_depth"] == PORTABLE_PATTERN_MAX_GROUP_DEPTH
    assert profile["max_nfa_states"] == PORTABLE_PATTERN_MAX_NFA_STATES
    assert profile["max_dfa_states"] == PORTABLE_PATTERN_MAX_DFA_STATES
    assert profile["max_dfa_transitions"] == PORTABLE_PATTERN_MAX_DFA_TRANSITIONS
    assert profile["max_schema_patterns"] == PORTABLE_PATTERN_MAX_SCHEMA_PATTERNS
    assert profile["max_schema_codepoints"] == PORTABLE_PATTERN_MAX_SCHEMA_CODEPOINTS
    assert profile["max_validation_work"] == PORTABLE_PATTERN_MAX_VALIDATION_WORK
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


def test_nested_quantifier_failure_is_linear_at_large_input_scale() -> None:
    # A backtracking engine takes exponential time on this classic ReDoS shape.
    # The bounded NFA consumes each code point once per active instruction.
    assert portable_pattern_matches("^(a+)+$", "a" * 100_000 + "!") is False


def test_normalized_character_classes_and_cache_retention_are_bounded() -> None:
    repeated_class = "[" + "a" * 1000 + "]"
    assert portable_pattern_matches(repeated_class, "b" * 100_000) is False
    assert portable_pattern_matches(repeated_class, "a") is True

    for index in range(PORTABLE_PATTERN_CACHE_SIZE + 8):
        pattern = f"^cache{index:02d}[a-c]+$"
        assert portable_pattern_matches(pattern, f"cache{index:02d}abc") is True
    patterns, transitions, maximum = portable_pattern_cache_info()
    assert patterns == PORTABLE_PATTERN_CACHE_SIZE
    assert transitions <= maximum


def test_adversarial_dfa_subsets_cannot_amplify_persistent_cache_memory() -> None:
    # Each successive input position creates a larger exact subset for this accepted
    # expression. State/transition counts alone do not bound the sum of those arrays.
    pattern = "(?:a|b)*a(?:a|b){1000}"
    assert portable_pattern_matches(pattern, "a" * 1001) is True
    assert portable_pattern_matches(pattern, "b" * 1001) is False

    aggregate, peak, aggregate_limit, per_engine_limit = _portable_pattern_cache_membership_info()
    assert peak <= per_engine_limit
    assert aggregate <= aggregate_limit


def test_validation_memo_reuses_identical_pattern_key_classification() -> None:
    value = "a" * 10_000
    assert portable_pattern_matches("z", value) is False
    with portable_pattern_validation_budget(len(value) + 20):
        assert portable_pattern_matches("z", value) is False
        assert portable_pattern_matches("z", value) is False


def test_aggregate_pattern_key_work_has_stable_structural_classification(tmp_path: Path) -> None:
    key = "a" * 120_000
    patterns = {f"z{index:02d}": True for index in range(70)}
    result = _validate(tmp_path, {key: 1}, {"type": "object", "patternProperties": patterns})
    assert result.structural.errors == [
        {
            "kind": "schema_invalid",
            "reason": "compile",
            "message": "compiled schema could not be compiled",
            "schema_path": "",
        }
    ]


def test_pattern_parser_limits_fail_closed_before_recursion_or_allocation() -> None:
    assert is_portable_pattern("(" * 64 + "a" + ")" * 64) is True
    assert is_portable_pattern("(" * 65 + "a" + ")" * 65) is False
    assert is_portable_pattern("a" * 1024) is True
    assert is_portable_pattern("a" * 1025) is False
    assert is_portable_pattern("(?:abcd){1000}") is True
    assert is_portable_pattern("(?:abcde){1000}") is False


def test_regex_sensitive_object_keywords_remain_linear_at_scale(tmp_path: Path) -> None:
    pattern = "^(a+)+$"
    adversarial_key = "a" * 50_000 + "!"

    additional = _validate(
        tmp_path,
        {adversarial_key: 1},
        {
            "type": "object",
            "patternProperties": {pattern: {"type": "integer"}},
            "additionalProperties": False,
        },
    )
    assert additional.structural.errors[0]["validator"] == "additionalProperties"
    assert structural_error_offending_property(additional.structural.errors[0]) == adversarial_key

    unevaluated = _validate(
        tmp_path,
        {adversarial_key: 1},
        {
            "type": "object",
            "allOf": [{"patternProperties": {pattern: {"type": "integer"}}}],
            "unevaluatedProperties": False,
        },
    )
    assert unevaluated.structural.errors[0]["validator"] == "unevaluatedProperties"
    assert structural_error_offending_property(unevaluated.structural.errors[0]) == adversarial_key


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
