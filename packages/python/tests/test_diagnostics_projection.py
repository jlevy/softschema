"""Shared diagnostic-v1, JSONL, and SARIF projection vectors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft4Validator, Draft202012Validator
from referencing import Registry, Resource

from softschema.core.diagnostics import (
    DiagnosticAggregateV1,
    DiagnosticResultV1,
    DiagnosticV1,
    diagnostic_rule_id,
    project_diagnostic_aggregate,
    project_diagnostic_result,
    project_diagnostic_sarif,
    project_validation_wire,
    serialize_diagnostic_jsonl,
)
from softschema.core.results import ArtifactInputResultWire
from softschema.core.value_domain import ValidationLimits
from tests.yaml_fixtures import load_yaml_fixture

ROOT = Path(__file__).parents[3]
DIAGNOSTICS = ROOT / "tests/diagnostics"
SCHEMAS = ROOT / "conformance/schemas"
WIRE_VECTORS = DIAGNOSTICS / "wire-vectors.yaml"
SARIF_VECTORS = DIAGNOSTICS / "sarif-vectors.yaml"


def _load(path: Path) -> dict[str, Any]:
    if path.suffix == ".yaml":
        return load_yaml_fixture(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _limits(raw: dict[str, Any]) -> ValidationLimits:
    return ValidationLimits(
        max_resource_bytes=raw["max_resource_bytes"],
        max_bundle_bytes=raw["max_bundle_bytes"],
        max_resources=raw["max_resources"],
        max_nodes_per_resource=raw["max_nodes_per_resource"],
        max_depth=raw["max_depth"],
        max_scalar_codepoints=raw["max_scalar_codepoints"],
    )


def _result(raw: object) -> DiagnosticResultV1:
    return cast(DiagnosticResultV1, raw)


def _plain(value: object) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _aggregate(wire: dict[str, Any], aggregate_id: str) -> DiagnosticAggregateV1:
    vector = next(item for item in wire["aggregates"] if item["id"] == aggregate_id)
    results = [_result(wire["results"][result_id]) for result_id in vector["result_ids"]]
    return project_diagnostic_aggregate(wire["profile"], _limits(wire["limits"]), results)


def _diagnostic_registry() -> tuple[dict[str, Any], Registry[Any]]:
    schemas = {path.name: _load(path) for path in sorted(SCHEMAS.glob("*.schema.json"))}
    registry: Registry[Any] = Registry()
    for schema in schemas.values():
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return schemas, registry


def test_shared_wire_vectors_project_exact_outcomes_and_validate() -> None:
    wire = _load(WIRE_VECTORS)
    schemas, registry = _diagnostic_registry()
    validator = Draft202012Validator(
        schemas["validation-result-diagnostic-v1.schema.json"], registry=registry
    )
    jsonl_validator = Draft202012Validator(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": (
                "urn:softschema:draft:conformance:validation-result-diagnostic-v1:v0"
                "#/$defs/jsonlRecord"
            ),
        },
        registry=registry,
    )

    for vector in wire["aggregates"]:
        aggregate = _aggregate(wire, vector["id"])
        assert aggregate["summary"] == vector["summary"]
        assert aggregate["ok"] is (vector["summary"]["exit_code"] == 0)
        assert list(validator.iter_errors(_plain(aggregate))) == []

        lines = serialize_diagnostic_jsonl(aggregate).removesuffix("\n").split("\n")
        assert len(lines) == len(vector["result_ids"])
        for line, result in zip(lines, aggregate["results"], strict=True):
            record = json.loads(line)
            assert record == {
                "format": "diagnostic-v1",
                "profile": wire["profile"],
                "limits": wire["limits"],
                "result": result,
            }
            assert "summary" not in record
            assert list(jsonl_validator.iter_errors(record)) == []
            assert line == json.dumps(
                record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )

    input_precedence = _aggregate(wire, "input-precedence-exit-2")
    assert input_precedence["summary"]["input_failed"] == 3
    assert input_precedence["summary"]["exit_code"] == 2
    ordered = _aggregate(wire, "unicode-code-point-order")["results"][0]["diagnostics"]
    assert [item.get("path") for item in ordered] == ["/", "/𐀀"]


def test_diagnostic_schema_rejects_duplicate_fields_and_wrong_outcomes() -> None:
    wire = _load(WIRE_VECTORS)
    schemas, registry = _diagnostic_registry()
    validator = Draft202012Validator(
        schemas["validation-result-diagnostic-v1.schema.json"], registry=registry
    )

    duplicate_source = _plain(_aggregate(wire, "success"))
    duplicate_source["results"][0]["source"] = "duplicated.md"
    assert not validator.is_valid(duplicate_source)

    duplicate_values = _plain(_aggregate(wire, "success"))
    validation = duplicate_values["results"][0]["validation"]
    assert validation is not None
    validation["values"] = {"duplicated": True}
    assert not validator.is_valid(duplicate_values)

    wrong_no_match_outcome = _plain(_aggregate(wire, "input-precedence-exit-2"))
    no_match = next(
        result
        for result in wrong_no_match_outcome["results"]
        if result["input"].get("reason") == "no_matches"
    )
    no_match["outcome"] = "validation_failed"
    assert not validator.is_valid(wrong_no_match_outcome)


def test_result_and_legacy_validation_projection_match_shared_wire() -> None:
    wire = _load(WIRE_VECTORS)
    for raw in wire["results"].values():
        expected = _result(raw)
        actual = project_diagnostic_result(
            expected["input"],
            expected["validation"],
            expected["diagnostics"],
        )
        assert actual == expected

    expected_validation = _result(wire["results"]["passed"])["validation"]
    assert expected_validation is not None
    legacy = {
        **expected_validation,
        "path": "artifacts/valid movie.md",
        "profile": "frontmatter-md",
        "values": {"movie": {"title": "Arrival", "year": 2016}},
    }
    assert project_validation_wire(legacy) == expected_validation
    assert diagnostic_rule_id("schema_violation", "$Ref") == ("softschema.schema_violation.ref")


def test_projection_rejects_invalid_profiles_sources_and_stale_summaries() -> None:
    wire = _load(WIRE_VECTORS)
    passed = _result(wire["results"]["passed"])
    with pytest.raises(ValueError, match="diagnostic profile"):
        project_diagnostic_aggregate(
            cast(Any, "invalid-profile"), _limits(wire["limits"]), [passed]
        )

    mismatched = cast(
        DiagnosticV1,
        cast(object, {**wire["results"]["binding"]["diagnostics"][0]}),
    )
    mismatched["source"] = "other.md"
    with pytest.raises(ValueError, match="source must match"):
        project_diagnostic_result(
            cast(ArtifactInputResultWire, wire["results"]["binding"]["input"]),
            None,
            [mismatched],
        )

    stale = _aggregate(wire, "success")
    stale["summary"]["exit_code"] = 1
    with pytest.raises(ValueError, match="summary does not match"):
        serialize_diagnostic_jsonl(stale)


def test_sarif_vectors_match_exactly_and_validate_against_pinned_oasis_schema() -> None:
    wire = _load(WIRE_VECTORS)
    vectors = _load(SARIF_VECTORS)
    schema_info = vectors["schema"]
    schema_path = DIAGNOSTICS / schema_info["path"]
    assert hashlib.sha256(schema_path.read_bytes()).hexdigest() == schema_info["sha256"]
    assert schema_info["sha256"] == (
        "c3b4bb2d6093897483348925aaa73af03b3e3f4bd4ca38cef26dcb4212a2682e"
    )
    official_validator = Draft4Validator(_load(schema_path))

    for vector in vectors["vectors"]:
        aggregate = _aggregate(wire, vector["aggregate_id"])
        sarif = project_diagnostic_sarif(aggregate)
        assert sarif == vector["sarif"]
        assert list(official_validator.iter_errors(sarif)) == []
        run = sarif["runs"][0]
        rule_ids = [rule["id"] for rule in run["tool"]["driver"]["rules"]]
        assert rule_ids == sorted(rule_ids)
        for result in run["results"]:
            assert rule_ids[result["ruleIndex"]] == result["ruleId"]

    exit_one = project_diagnostic_sarif(_aggregate(wire, "validation-exit-1"))
    exit_two = project_diagnostic_sarif(_aggregate(wire, "input-precedence-exit-2"))
    assert exit_one["runs"][0]["invocations"] == [{"executionSuccessful": True, "exitCode": 1}]
    assert exit_two["runs"][0]["invocations"] == [{"executionSuccessful": False, "exitCode": 2}]
