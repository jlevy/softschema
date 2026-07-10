"""Pure diagnostic-v1, JSONL, and SARIF wire projections."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any, Literal, NotRequired, Required, TypedDict, cast
from urllib.parse import quote

from softschema.core.metadata import SchemaProfile
from softschema.core.results import (
    ArtifactInputResultWire,
)
from softschema.core.value_domain import JsonValue, ValidationLimits

DIAGNOSTIC_FORMAT = "diagnostic-v1"
SARIF_SCHEMA_URI = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json"
)
SARIF_VERSION = "2.1.0"
_MAX_SORT_COORDINATE = 9_007_199_254_740_991
_RULE_CODE_PATTERN = re.compile(r"[^a-z0-9_.-]+")

DiagnosticCategory = Literal[
    "input", "parse", "binding", "schema", "structural", "semantic", "warning"
]
DiagnosticSeverity = Literal["error", "warning", "info"]
DiagnosticOutcome = Literal["passed", "validation_failed", "input_failed"]
DiagnosticRuleFamily = Literal[
    "input_error",
    "parse_error",
    "schema_invalid",
    "schema_violation",
    "artifact",
    "semantic",
    "warning",
]


class DiagnosticLimitsWire(TypedDict):
    """Snake-case validation budgets embedded in diagnostic wire records."""

    max_resource_bytes: int
    max_bundle_bytes: int
    max_resources: int
    max_nodes_per_resource: int
    max_depth: int
    max_scalar_codepoints: int


class DiagnosticV1(TypedDict):
    """One normalized, source-positioned diagnostic."""

    category: Required[DiagnosticCategory]
    rule_id: Required[str]
    severity: Required[DiagnosticSeverity]
    message: Required[str]
    source: Required[str]
    path: NotRequired[str]
    schema_source: NotRequired[str]
    schema_path: NotRequired[str]
    line: NotRequired[int]
    column: NotRequired[int]


class DiagnosticWarningWire(TypedDict):
    """Warning retained in the de-duplicated validation payload."""

    code: str
    message: str
    severity: Literal["info", "warning"]


class DiagnosticValidationWire(TypedDict):
    """Legacy validation payload without duplicated source, values, or profile fields."""

    contract: dict[str, JsonValue] | None
    contract_id: str
    document_metadata: dict[str, JsonValue] | None
    semantic: dict[str, JsonValue]
    status: Literal["soft", "permissive", "enforced"]
    structural: dict[str, JsonValue]
    warnings: list[DiagnosticWarningWire]


class DiagnosticResultV1(TypedDict):
    """One diagnostic-v1 artifact result."""

    outcome: DiagnosticOutcome
    input: ArtifactInputResultWire
    validation: DiagnosticValidationWire | None
    diagnostics: list[DiagnosticV1]


class DiagnosticSummaryV1(TypedDict):
    """Exact partition and process exit for one diagnostic aggregate."""

    total: int
    passed: int
    validation_failed: int
    input_failed: int
    exit_code: Literal[0, 1, 2]


class DiagnosticAggregateV1(TypedDict):
    """Versioned multi-artifact diagnostic wire result."""

    format: Literal["diagnostic-v1"]
    profile: Literal["frontmatter-md", "pure-yaml"]
    limits: DiagnosticLimitsWire
    ok: bool
    results: list[DiagnosticResultV1]
    summary: DiagnosticSummaryV1


class DiagnosticJsonlRecordV1(TypedDict):
    """Self-describing JSONL envelope for one artifact result."""

    format: Literal["diagnostic-v1"]
    profile: Literal["frontmatter-md", "pure-yaml"]
    limits: DiagnosticLimitsWire
    result: DiagnosticResultV1


def diagnostic_rule_id(family: DiagnosticRuleFamily, code: str) -> str:
    """Build a stable lowercase rule identifier from a portable issue code."""
    normalized = _RULE_CODE_PATTERN.sub("_", code.lower().removeprefix("$")).strip("_.-")
    if not normalized:
        raise ValueError("diagnostic rule code must contain an ASCII letter or digit")
    return f"softschema.{family}.{normalized}"


def validation_limits_wire(limits: ValidationLimits) -> DiagnosticLimitsWire:
    """Project runtime validation budgets to their exact snake-case wire spelling."""
    return {
        "max_resource_bytes": limits.max_resource_bytes,
        "max_bundle_bytes": limits.max_bundle_bytes,
        "max_resources": limits.max_resources,
        "max_nodes_per_resource": limits.max_nodes_per_resource,
        "max_depth": limits.max_depth,
        "max_scalar_codepoints": limits.max_scalar_codepoints,
    }


def project_validation_wire(validation: Mapping[str, Any]) -> DiagnosticValidationWire:
    """Remove legacy path/value/profile duplication from a validation wire payload."""
    fields = (
        "contract",
        "contract_id",
        "document_metadata",
        "semantic",
        "status",
        "structural",
        "warnings",
    )
    missing = [field for field in fields if field not in validation]
    if missing:
        raise ValueError(f"validation wire is missing required field: {missing[0]}")
    projected = {field: deepcopy(validation[field]) for field in fields}
    return cast(DiagnosticValidationWire, cast(object, projected))


def project_diagnostic_result(
    input_result: ArtifactInputResultWire,
    validation: DiagnosticValidationWire | None,
    diagnostics: Sequence[DiagnosticV1],
) -> DiagnosticResultV1:
    """Build one result and derive its outcome from discriminated input/validation state."""
    normalized_diagnostics = _normalized_diagnostics(input_result["source"], diagnostics)
    outcome = _result_outcome(input_result, validation, normalized_diagnostics)
    return {
        "outcome": outcome,
        "input": deepcopy(input_result),
        "validation": deepcopy(validation),
        "diagnostics": normalized_diagnostics,
    }


def project_diagnostic_aggregate(
    profile: SchemaProfile | Literal["frontmatter-md", "pure-yaml"],
    limits: ValidationLimits,
    results: Sequence[DiagnosticResultV1],
) -> DiagnosticAggregateV1:
    """Build an aggregate with an exact result partition and 2 > 1 > 0 exit precedence."""
    if not results:
        raise ValueError("diagnostic aggregate requires at least one result")
    normalized_results = [_normalize_result(result) for result in results]
    passed = sum(result["outcome"] == "passed" for result in normalized_results)
    validation_failed = sum(
        result["outcome"] == "validation_failed" for result in normalized_results
    )
    input_failed = sum(result["outcome"] == "input_failed" for result in normalized_results)
    exit_code: Literal[0, 1, 2]
    if input_failed:
        exit_code = 2
    elif validation_failed:
        exit_code = 1
    else:
        exit_code = 0
    profile_value = profile.value if isinstance(profile, SchemaProfile) else profile
    if profile_value not in ("frontmatter-md", "pure-yaml"):
        raise ValueError("diagnostic profile must be frontmatter-md or pure-yaml")
    return {
        "format": DIAGNOSTIC_FORMAT,
        "profile": profile_value,
        "limits": validation_limits_wire(limits),
        "ok": exit_code == 0,
        "results": normalized_results,
        "summary": {
            "total": len(normalized_results),
            "passed": passed,
            "validation_failed": validation_failed,
            "input_failed": input_failed,
            "exit_code": exit_code,
        },
    }


def serialize_diagnostic_jsonl(aggregate: DiagnosticAggregateV1) -> str:
    """Serialize one compact, sorted, self-describing line per result and no summary."""
    _assert_aggregate_summary(aggregate)
    lines = []
    for result in aggregate["results"]:
        record: DiagnosticJsonlRecordV1 = {
            "format": DIAGNOSTIC_FORMAT,
            "profile": aggregate["profile"],
            "limits": aggregate["limits"],
            "result": result,
        }
        lines.append(_canonical_json(record))
    return "\n".join(lines) + "\n"


def project_diagnostic_sarif(aggregate: DiagnosticAggregateV1) -> dict[str, Any]:
    """Project diagnostic-v1 into deterministic SARIF 2.1.0 Errata 01 JSON."""
    _assert_aggregate_summary(aggregate)
    diagnostics: list[tuple[DiagnosticOutcome, DiagnosticV1]] = []
    for result in aggregate["results"]:
        diagnostics.extend((result["outcome"], item) for item in result["diagnostics"])
    rule_ids = sorted({diagnostic["rule_id"] for _, diagnostic in diagnostics})
    rule_indexes = {rule_id: index for index, rule_id in enumerate(rule_ids)}
    artifact_sources = {result["input"]["source"] for result in aggregate["results"]}
    schema_sources = {
        diagnostic["schema_source"]
        for _, diagnostic in diagnostics
        if "schema_source" in diagnostic
    }
    sources = artifact_sources | schema_sources
    artifacts = sorted(
        (_artifact_uri(source, allow_uri=source in schema_sources), source) for source in sources
    )
    artifact_indexes = {source: index for index, (_, source) in enumerate(artifacts)}
    sarif_results = [
        _sarif_result(outcome, diagnostic, rule_indexes, artifact_indexes)
        for outcome, diagnostic in diagnostics
    ]
    run: dict[str, Any] = {
        "tool": {
            "driver": {
                "name": "softschema",
                "informationUri": "https://github.com/jlevy/softschema",
                "rules": [{"id": rule_id} for rule_id in rule_ids],
            }
        },
        "invocations": [
            {
                "executionSuccessful": aggregate["summary"]["exit_code"] != 2,
                "exitCode": aggregate["summary"]["exit_code"],
            }
        ],
        "artifacts": [{"location": {"uri": uri}} for uri, _ in artifacts],
        "results": sarif_results,
        "columnKind": "unicodeCodePoints",
        "properties": {
            "softschemaFormat": DIAGNOSTIC_FORMAT,
            "softschemaProfile": aggregate["profile"],
            "softschemaLimits": aggregate["limits"],
            "softschemaSummary": aggregate["summary"],
        },
    }
    return {
        "$schema": SARIF_SCHEMA_URI,
        "version": SARIF_VERSION,
        "runs": [run],
    }


def _normalized_diagnostics(source: str, diagnostics: Sequence[DiagnosticV1]) -> list[DiagnosticV1]:
    copied = [deepcopy(diagnostic) for diagnostic in diagnostics]
    for diagnostic in copied:
        if diagnostic["source"] != source:
            raise ValueError("diagnostic source must match input.source")
        if "column" in diagnostic and "line" not in diagnostic:
            raise ValueError("diagnostic column requires line")
    return sorted(copied, key=_diagnostic_sort_key)


def _diagnostic_sort_key(diagnostic: DiagnosticV1) -> tuple[Any, ...]:
    return (
        diagnostic.get("schema_source", diagnostic["source"]),
        diagnostic.get("line", _MAX_SORT_COORDINATE),
        diagnostic.get("column", _MAX_SORT_COORDINATE),
        diagnostic["rule_id"],
        diagnostic.get("path", ""),
        diagnostic.get("schema_path", ""),
        diagnostic["message"],
        diagnostic["severity"],
    )


def _result_outcome(
    input_result: ArtifactInputResultWire,
    validation: DiagnosticValidationWire | None,
    diagnostics: Sequence[DiagnosticV1],
) -> DiagnosticOutcome:
    kind = input_result["kind"]
    error_diagnostics = [item for item in diagnostics if item["severity"] == "error"]
    if kind == "input_error":
        if validation is not None:
            raise ValueError("input failure cannot contain validation")
        if not any(item["category"] == "input" for item in error_diagnostics):
            raise ValueError("input failure requires an input error diagnostic")
        return "input_failed"
    if kind == "parse_error":
        if validation is not None:
            raise ValueError("parse failure cannot contain validation")
        if not any(item["category"] == "parse" for item in error_diagnostics):
            raise ValueError("parse failure requires a parse error diagnostic")
        return "validation_failed"
    if kind != "artifact_input":
        raise ValueError(f"unsupported artifact input kind: {kind}")
    if validation is None:
        if not any(item["category"] == "binding" for item in error_diagnostics):
            raise ValueError("unbound artifact requires a binding error diagnostic")
        return "validation_failed"
    validation_ok = bool(validation["structural"]["ok"]) and bool(validation["semantic"]["ok"])
    if validation_ok:
        if error_diagnostics:
            raise ValueError("passed validation cannot contain error diagnostics")
        return "passed"
    if not error_diagnostics:
        raise ValueError("failed validation requires an error diagnostic")
    return "validation_failed"


def _normalize_result(result: DiagnosticResultV1) -> DiagnosticResultV1:
    diagnostics = _normalized_diagnostics(result["input"]["source"], result["diagnostics"])
    expected = _result_outcome(result["input"], result["validation"], diagnostics)
    if result["outcome"] != expected:
        raise ValueError(f"result outcome must be {expected}")
    return {
        "outcome": result["outcome"],
        "input": deepcopy(result["input"]),
        "validation": deepcopy(result["validation"]),
        "diagnostics": diagnostics,
    }


def _assert_aggregate_summary(aggregate: DiagnosticAggregateV1) -> None:
    rebuilt = project_diagnostic_aggregate(
        aggregate["profile"],
        _limits_from_wire(aggregate["limits"]),
        aggregate["results"],
    )
    if rebuilt["summary"] != aggregate["summary"] or rebuilt["ok"] != aggregate["ok"]:
        raise ValueError("diagnostic aggregate summary does not match results")


def _limits_from_wire(limits: DiagnosticLimitsWire) -> ValidationLimits:
    return ValidationLimits(
        max_resource_bytes=limits["max_resource_bytes"],
        max_bundle_bytes=limits["max_bundle_bytes"],
        max_resources=limits["max_resources"],
        max_nodes_per_resource=limits["max_nodes_per_resource"],
        max_depth=limits["max_depth"],
        max_scalar_codepoints=limits["max_scalar_codepoints"],
    )


def _sarif_result(
    outcome: DiagnosticOutcome,
    diagnostic: DiagnosticV1,
    rule_indexes: Mapping[str, int],
    artifact_indexes: Mapping[str, int],
) -> dict[str, Any]:
    schema_anchor = "schema_source" in diagnostic
    anchor_source = diagnostic.get("schema_source", diagnostic["source"])
    physical_location: dict[str, JsonValue] = {
        "artifactLocation": {
            "uri": _artifact_uri(anchor_source, allow_uri=schema_anchor),
            "index": artifact_indexes[anchor_source],
        }
    }
    if "line" in diagnostic:
        region: dict[str, JsonValue] = {"startLine": diagnostic["line"]}
        if "column" in diagnostic:
            region["startColumn"] = diagnostic["column"]
        physical_location["region"] = region
    properties: dict[str, JsonValue] = {
        "softschemaCategory": diagnostic["category"],
        "softschemaOutcome": outcome,
        "softschemaSource": diagnostic["source"],
    }
    optional_properties = {
        "path": "softschemaPath",
        "schema_source": "softschemaSchemaSource",
        "schema_path": "softschemaSchemaPath",
    }
    for field, property_name in optional_properties.items():
        if field in diagnostic:
            properties[property_name] = cast(JsonValue, diagnostic[field])
    level = {"error": "error", "warning": "warning", "info": "note"}[diagnostic["severity"]]
    return {
        "ruleId": diagnostic["rule_id"],
        "ruleIndex": rule_indexes[diagnostic["rule_id"]],
        "level": level,
        "message": {"text": diagnostic["message"]},
        "locations": [{"physicalLocation": physical_location}],
        "properties": properties,
    }


def _artifact_uri(source: str, *, allow_uri: bool) -> str:
    if re.match(r"^[A-Za-z]:/", source):
        return "file:///" + source[:2] + quote(source[2:], safe="/-._~")
    if source.startswith("//"):
        return "file:" + quote(source, safe="/-._~")
    if source.startswith("/"):
        return "file://" + quote(source, safe="/-._~")
    if allow_uri and re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", source):
        return _encode_absolute_uri(source)
    return quote(source, safe="/-._~")


def _encode_absolute_uri(source: str) -> str:
    parts: list[str] = []
    index = 0
    while index < len(source):
        if (
            source[index] == "%"
            and index + 2 < len(source)
            and all(
                character in "0123456789abcdefABCDEF" for character in source[index + 1 : index + 3]
            )
        ):
            parts.append("%" + source[index + 1 : index + 3].upper())
            index += 3
            continue
        parts.append(quote(source[index], safe=";/?:@&=+$,#-_.!~*'()[]"))
        index += 1
    return "".join(parts)


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
