"""Official Python adapter for language-neutral conformance vector suites."""

from __future__ import annotations

import json
import math
import re
import sys
import tempfile
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any, Never

from pydantic import ValidationError

from softschema import canonicalize_json_schema, validate_structural
from softschema.core import (
    DEFAULT_VALIDATION_LIMITS,
    PortableValueError,
    is_portable_pattern,
    normalize_portable_value,
    portable_pattern_matches,
    project_diagnostic_aggregate,
    project_diagnostic_sarif,
    serialize_diagnostic_jsonl,
    validate_contract_id,
    validate_extension_namespace,
    validate_schema_id,
)
from softschema.core.value_domain import ValidationLimits
from softschema.models import parse_schema_metadata
from softschema.value_domain import PortableYamlSyntaxError, parse_portable_yaml_with_locations

RESULT_FORMAT = "softschema-vector-results-v1"
REQUEST_FORMAT = "softschema-vector-suite-v1"
MAX_REQUEST_BYTES = 16 * 1024 * 1024
MAX_REQUEST_CASES = 4096
MAX_JSON_DEPTH = 128
MAX_JSON_NODES = 100_000
MAX_SAFE_INTEGER = 9_007_199_254_740_991
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LIMIT_FIELDS = frozenset(
    {
        "max_resource_bytes",
        "max_bundle_bytes",
        "max_resources",
        "max_nodes_per_resource",
        "max_depth",
        "max_scalar_codepoints",
    }
)
POSITIVE_LIMIT_FIELDS = frozenset({"max_resources", "max_nodes_per_resource", "max_depth"})
OPERATIONS = frozenset(
    {
        "canonicalize",
        "diagnostic-summary",
        "identity",
        "metadata",
        "pattern",
        "portable-yaml",
        "validate-structural",
    }
)


class AdapterRequestError(ValueError):
    """A malformed or unsupported vector adapter request."""


def _has_exact_fields(
    value: dict[str, Any], required: frozenset[str], allowed: frozenset[str]
) -> bool:
    fields = set(value)
    return required.issubset(fields) and fields.issubset(allowed)


def _invalid_case_input(index: int, operation: str, detail: str) -> Never:
    raise AdapterRequestError(f"request case {index} input for {operation} {detail}")


def _validate_limit_fields(value: Any, index: int, operation: str) -> None:
    if not isinstance(value, dict) or not set(value).issubset(LIMIT_FIELDS):
        _invalid_case_input(index, operation, "limits has invalid fields")
    for field, limit in value.items():
        minimum = 1 if field in POSITIVE_LIMIT_FIELDS else 0
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int | float)
            or not math.isfinite(limit)
            or not float(limit).is_integer()
            or limit < minimum
            or limit > MAX_SAFE_INTEGER
        ):
            qualifier = "positive" if minimum == 1 else "nonnegative"
            _invalid_case_input(
                index,
                operation,
                f"limit {field} must be a {qualifier} safe integer",
            )
        value[field] = int(limit)


def _validate_case_input(operation: str, value: dict[str, Any], index: int) -> None:
    required: frozenset[str]
    allowed: frozenset[str]
    if operation == "canonicalize":
        required = frozenset({"schema"})
        allowed = required | {"instances"}
        if not _has_exact_fields(value, required, allowed):
            _invalid_case_input(index, operation, "has missing or unexpected fields")
        if not isinstance(value["schema"], dict):
            _invalid_case_input(index, operation, "schema must be an object")
        if "instances" in value and not isinstance(value["instances"], list):
            _invalid_case_input(index, operation, "instances must be an array")
        return
    if operation == "diagnostic-summary":
        required = frozenset({"profile", "results"})
        if not _has_exact_fields(value, required, required):
            _invalid_case_input(index, operation, "has missing or unexpected fields")
        if not isinstance(value["profile"], str) or value["profile"] not in {
            "frontmatter-md",
            "pure-yaml",
        }:
            _invalid_case_input(index, operation, "profile is unsupported")
        if not isinstance(value["results"], list) or not value["results"]:
            _invalid_case_input(index, operation, "results must be a non-empty array")
        return
    if operation == "identity":
        required = frozenset({"kind", "value"})
        if not _has_exact_fields(value, required, required):
            _invalid_case_input(index, operation, "has missing or unexpected fields")
        if not isinstance(value["kind"], str) or value["kind"] not in {
            "contract",
            "extension",
            "schema",
        }:
            _invalid_case_input(index, operation, "kind is unsupported")
        return
    if operation == "metadata":
        required = frozenset({"raw"})
        if not _has_exact_fields(value, required, required):
            _invalid_case_input(index, operation, "has missing or unexpected fields")
        return
    if operation == "pattern":
        required = frozenset({"pattern"})
        allowed = required | {"value"}
        if not _has_exact_fields(value, required, allowed):
            _invalid_case_input(index, operation, "has missing or unexpected fields")
        if not isinstance(value["pattern"], str):
            _invalid_case_input(index, operation, "pattern must be a string")
        if "value" in value and not isinstance(value["value"], str):
            _invalid_case_input(index, operation, "value must be a string")
        return
    if operation == "portable-yaml":
        required = frozenset({"text"})
        allowed = required | {"limits", "include_location", "source_pointers"}
        if not _has_exact_fields(value, required, allowed):
            _invalid_case_input(index, operation, "has missing or unexpected fields")
        if not isinstance(value["text"], str):
            _invalid_case_input(index, operation, "text must be a string")
        if "limits" in value:
            _validate_limit_fields(value["limits"], index, operation)
        if "include_location" in value and not isinstance(value["include_location"], bool):
            _invalid_case_input(index, operation, "include_location must be a boolean")
        if "source_pointers" in value:
            pointers = value["source_pointers"]
            if (
                not isinstance(pointers, list)
                or not pointers
                or any(not isinstance(pointer, str) for pointer in pointers)
                or len(set(pointers)) != len(pointers)
            ):
                _invalid_case_input(
                    index,
                    operation,
                    "source_pointers must be a non-empty array of unique strings",
                )
        return
    if operation == "validate-structural":
        required = frozenset({"schema", "values"})
        allowed = required | {"resources", "strict_extras"}
        if not _has_exact_fields(value, required, allowed):
            _invalid_case_input(index, operation, "has missing or unexpected fields")
        if not isinstance(value["schema"], dict):
            _invalid_case_input(index, operation, "schema must be an object")
        if "resources" in value and not isinstance(value["resources"], dict):
            _invalid_case_input(index, operation, "resources must be an object")
        if "strict_extras" in value and not isinstance(value["strict_extras"], bool):
            _invalid_case_input(index, operation, "strict_extras must be a boolean")
        return
    raise AdapterRequestError("request operation is unsupported")


def _parse_request(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_REQUEST_BYTES:
        raise AdapterRequestError("request exceeds the byte limit")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise AdapterRequestError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise AdapterRequestError(f"non-finite JSON number: {value}")

    def parse_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            reject_constant(value)
        return parsed

    try:
        request = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
            parse_float=parse_float,
        )
        _validate_json_structure(request)
    except AdapterRequestError:
        raise
    except (UnicodeError, RecursionError, ValueError) as exc:
        raise AdapterRequestError(f"request is not strict UTF-8 JSON: {exc}") from exc
    if not isinstance(request, dict):
        raise AdapterRequestError("request must be an object")
    required = {"format", "id", "operation", "cases"}
    allowed = required | {"description"}
    if not required.issubset(request) or not set(request).issubset(allowed):
        raise AdapterRequestError("request has missing or unexpected fields")
    if request["format"] != REQUEST_FORMAT:
        raise AdapterRequestError("request has an unsupported format")
    if not isinstance(request["id"], str) or IDENTIFIER_PATTERN.fullmatch(request["id"]) is None:
        raise AdapterRequestError("request id must be a lowercase kebab identifier")
    operation = request["operation"]
    if not isinstance(operation, str) or operation not in OPERATIONS:
        raise AdapterRequestError("request operation is unsupported")
    if "description" in request and (
        not isinstance(request["description"], str) or not request["description"]
    ):
        raise AdapterRequestError("request description must be a non-empty string")
    cases = request["cases"]
    if not isinstance(cases, list) or not cases or len(cases) > MAX_REQUEST_CASES:
        raise AdapterRequestError("request cases must be a non-empty array")
    case_ids: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise AdapterRequestError(f"request case {index} must be an object")
        case_required = {"id", "input", "expected"}
        case_allowed = case_required | {"description"}
        if not case_required.issubset(case) or not set(case).issubset(case_allowed):
            raise AdapterRequestError(f"request case {index} has invalid fields")
        case_id = case["id"]
        if (
            not isinstance(case_id, str)
            or IDENTIFIER_PATTERN.fullmatch(case_id) is None
            or case_id in case_ids
        ):
            raise AdapterRequestError(f"request case {index} has an invalid id")
        case_ids.add(case_id)
        if not isinstance(case["input"], dict):
            raise AdapterRequestError(f"request case {index} input must be an object")
        if not isinstance(case["expected"], dict):
            raise AdapterRequestError(f"request case {index} expected must be an object")
        if "description" in case and (
            not isinstance(case["description"], str) or not case["description"]
        ):
            raise AdapterRequestError(
                f"request case {index} description must be a non-empty string"
            )
        _validate_case_input(operation, case["input"], index)
    return request


def _validate_json_structure(value: Any) -> None:
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise AdapterRequestError("request exceeds the depth limit")
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise AdapterRequestError("request exceeds the node limit")
        if isinstance(current, str):
            try:
                current.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise AdapterRequestError(
                    "request contains an invalid Unicode scalar value"
                ) from exc
        elif isinstance(current, dict):
            for key in current:
                try:
                    key.encode("utf-8", errors="strict")
                except UnicodeEncodeError as exc:
                    raise AdapterRequestError(
                        "request contains an invalid Unicode scalar key"
                    ) from exc
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)


def _identity(case: dict[str, Any]) -> dict[str, Any]:
    validators: dict[str, Callable[[object], str]] = {
        "contract": validate_contract_id,
        "extension": validate_extension_namespace,
        "schema": validate_schema_id,
    }
    try:
        value = validators[case["kind"]](case["value"])
    except (KeyError, TypeError, ValueError):
        return {"ok": False}
    return {"ok": True, "value": value}


def _diagnostic_summary(case: dict[str, Any]) -> dict[str, Any]:
    aggregate = project_diagnostic_aggregate(
        case["profile"], DEFAULT_VALIDATION_LIMITS, case["results"]
    )
    jsonl = serialize_diagnostic_jsonl(aggregate)
    sarif = project_diagnostic_sarif(aggregate)
    run = sarif["runs"][0]
    return {
        "ok": aggregate["ok"],
        "summary": aggregate["summary"],
        "outcomes": [result["outcome"] for result in aggregate["results"]],
        "rule_ids": [
            diagnostic["rule_id"]
            for result in aggregate["results"]
            for diagnostic in result["diagnostics"]
        ],
        "jsonl_records": len(jsonl.splitlines()),
        "sarif": {
            "artifacts": len(run["artifacts"]),
            "column_kind": run["columnKind"],
            "execution_successful": run["invocations"][0]["executionSuccessful"],
            "exit_code": run["invocations"][0]["exitCode"],
            "results": len(run["results"]),
            "rules": [rule["id"] for rule in run["tool"]["driver"]["rules"]],
        },
    }


def _metadata(case: dict[str, Any]) -> dict[str, Any]:
    try:
        metadata = parse_schema_metadata(case.get("raw"))
    except (TypeError, ValidationError, ValueError):
        return {"ok": False}
    value = None if metadata is None else metadata.model_dump(mode="json", by_alias=True)
    return {"ok": True, "value": value}


def _pattern(case: dict[str, Any]) -> dict[str, Any]:
    pattern = case["pattern"]
    supported = is_portable_pattern(pattern)
    result: dict[str, Any] = {"ok": True, "supported": supported}
    if "value" in case:
        result["matches"] = portable_pattern_matches(pattern, case["value"]) if supported else None
    return result


def _portable_yaml(case: dict[str, Any]) -> dict[str, Any]:
    limits = ValidationLimits(**case.get("limits", {}))
    try:
        parsed = parse_portable_yaml_with_locations(case["text"], limits=limits)
    except PortableYamlSyntaxError as exc:
        return _yaml_error("syntax", exc, include_location=case.get("include_location", False))
    except PortableValueError as exc:
        return _yaml_error(
            "value_domain", exc, include_location=case.get("include_location", False)
        )
    result: dict[str, Any] = {"ok": True, "value": parsed.value}
    pointers = case.get("source_pointers")
    if pointers is not None:
        sources: dict[str, Any] = {}
        for pointer in pointers:
            node = parsed.source_map.node(pointer)
            if node is None:
                raise AdapterRequestError(f"portable-yaml source pointer is unmapped: {pointer}")
            sources[pointer] = {
                "start": {"line": node.value.start.line, "column": node.value.start.column},
                "end": {"line": node.value.end.line, "column": node.value.end.column},
            }
        result["sources"] = sources
    return result


def _yaml_error(
    kind: str,
    error: PortableValueError | PortableYamlSyntaxError,
    *,
    include_location: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {"ok": False, "kind": kind, "path": error.path}
    if include_location and error.line is not None:
        result["line"] = error.line
    if include_location and error.column is not None:
        result["column"] = error.column
    return result


def _structural_result(
    values: Any,
    schema: dict[str, Any],
    *,
    strict_extras: bool = False,
    resources: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = (json.dumps(schema, ensure_ascii=False, allow_nan=False) + "\n").encode()
    with tempfile.TemporaryDirectory(prefix="softschema-conformance-") as directory:
        schema_path = Path(directory) / "schema.json"
        schema_path.write_bytes(data)
        result = validate_structural(
            values,
            schema_path,
            strict_extras=strict_extras,
            resources=resources or {},
        )
    return asdict(result)


def _canonicalize(case: dict[str, Any]) -> dict[str, Any]:
    raw = case["schema"]
    transformed = canonicalize_json_schema(raw)
    canonical, _size = normalize_portable_value(transformed)
    if not isinstance(canonical, dict):  # defensive: schemas are mappings
        raise TypeError("canonical schema root must be a mapping")
    validity = [
        {
            "raw": _structural_result(instance, raw)["ok"],
            "canonical": _structural_result(instance, canonical)["ok"],
        }
        for instance in case.get("instances", [])
    ]
    return {"ok": True, "value": canonical, "validity": validity}


def _validate_structural(case: dict[str, Any]) -> dict[str, Any]:
    return _structural_result(
        case["values"],
        case["schema"],
        strict_extras=case.get("strict_extras", False),
        resources=case.get("resources", {}),
    )


def _execute(operation: str, case: dict[str, Any]) -> Any:
    if operation == "canonicalize":
        return _canonicalize(case)
    if operation == "diagnostic-summary":
        return _diagnostic_summary(case)
    if operation == "identity":
        return _identity(case)
    if operation == "metadata":
        return _metadata(case)
    if operation == "pattern":
        return _pattern(case)
    if operation == "portable-yaml":
        return _portable_yaml(case)
    if operation == "validate-structural":
        return _validate_structural(case)
    raise ValueError(f"unsupported vector operation: {operation}")


def main() -> int:
    try:
        request = _parse_request(sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1))
        operation = request["operation"]
        results = [
            {"id": case["id"], "actual": _execute(operation, case["input"])}
            for case in request["cases"]
        ]
        output = json.dumps(
            {"format": RESULT_FORMAT, "id": request["id"], "results": results},
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    except AdapterRequestError as exc:
        print(f"softschema vector adapter: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print("softschema vector adapter: request execution failed", file=sys.stderr)
        return 2
    sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
