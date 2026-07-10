"""Contract and compiled-schema identity boundaries."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from frontmatter_format import read_yaml_file
from pydantic import BaseModel, ValidationError

from softschema import (
    DEFAULT_VALIDATION_LIMITS,
    Contract,
    Contracts,
    SchemaView,
    compile_model,
    validate_artifact,
    validate_contract_id,
    validate_schema_id,
    validate_structural,
)


class _Sample(BaseModel):
    name: str


class _GenerationMustNotRun(BaseModel):
    name: str

    @classmethod
    def model_json_schema(  # pyright: ignore[reportImplicitOverride]
        cls, *args: object, **kwargs: object
    ) -> dict[str, object]:
        raise AssertionError("schema generation ran before identity validation")


_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_ID_VECTORS = json.loads(
    (_ROOT / "tests/identity/schema-id-vectors.json").read_text(encoding="utf-8")
)
_NESTED_RESOURCE_VECTORS = json.loads(
    (_ROOT / "tests/identity/nested-resource-vectors.json").read_text(encoding="utf-8")
)


def _structural_output(result: Any) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "errors": result.errors,
        "engine": result.engine,
        "skipped_reason": result.skipped_reason,
    }


def _schema_at_location(pointer: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current: dict[str, Any] | list[Any] = root
    parts = pointer.removeprefix("/").split("/")
    for index, part in enumerate(parts):
        last = index == len(parts) - 1
        next_part = None if last else parts[index + 1]
        value: Any = {"$id": "child/"} if last else ([] if next_part == "0" else {})
        if isinstance(current, list):
            assert part == "0"
            current.append(value)
        else:
            current[part] = value
        current = value
    return root


@pytest.mark.parametrize(
    "contract_id",
    ["Name", "example.docs:Record/v1", "a_b:record/2026-07"],
)
def test_contract_id_validator_is_the_public_boundary(contract_id: str) -> None:
    assert validate_contract_id(contract_id) == contract_id
    assert Contract(id=contract_id).id == contract_id


@pytest.mark.parametrize("contract_id", ["", "bad id", "ns:", "a::B", "Name/v1/v2"])
def test_contract_id_is_rejected_by_contract_registry_and_compiler(
    contract_id: str, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="contract ID"):
        validate_contract_id(contract_id)
    with pytest.raises(ValidationError):
        Contract(id=contract_id)

    registry = Contracts()
    with pytest.raises(ValueError, match="contract ID"):
        registry.resolve(contract_id)
    with pytest.raises(ValueError, match="contract ID"):
        validate_artifact(tmp_path / "must-not-be-read.md", contract_id=contract_id)

    out = tmp_path / "must-not-exist.yaml"
    with pytest.raises(ValueError, match="contract ID"):
        compile_model(_GenerationMustNotRun, out, contract_id=contract_id)
    assert not out.exists()


@pytest.mark.parametrize("schema_id", _SCHEMA_ID_VECTORS["valid"])
def test_schema_id_validator_accepts_canonical_absolute_identifiers(schema_id: str) -> None:
    assert validate_schema_id(schema_id) == schema_id


@pytest.mark.parametrize("schema_id", _SCHEMA_ID_VECTORS["invalid"])
def test_schema_id_is_rejected_before_generation_or_write(schema_id: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="schema ID"):
        validate_schema_id(schema_id)

    out = tmp_path / "must-not-exist.yaml"
    with pytest.raises(ValueError, match="schema ID"):
        compile_model(
            _GenerationMustNotRun,
            out,
            contract_id="example.docs:Record/v1",
            schema_id=schema_id,
        )
    assert not out.exists()


def test_compiler_keeps_contract_and_schema_identity_independent(tmp_path: Path) -> None:
    out = tmp_path / "schema.yaml"
    compile_model(
        _Sample,
        out,
        contract_id="example.docs:Record/v1",
        schema_id="https://schemas.example/softschema/record/v1",
    )

    schema = read_yaml_file(out)
    assert schema["$id"] == "https://schemas.example/softschema/record/v1"
    assert schema["x-softschema"]["contract"] == "example.docs:Record/v1"


def test_contract_id_alone_does_not_create_json_schema_id(tmp_path: Path) -> None:
    out = tmp_path / "schema.yaml"
    compile_model(_Sample, out, contract_id="example.docs:Record/v1")

    schema = read_yaml_file(out)
    assert "$id" not in schema
    assert schema["x-softschema"]["contract"] == "example.docs:Record/v1"


def test_compiler_requires_a_contract_before_generation_or_write(tmp_path: Path) -> None:
    out = tmp_path / "must-not-exist.yaml"
    compiler: Any = compile_model

    with pytest.raises(TypeError, match="contract_id"):
        compiler(_GenerationMustNotRun, out)

    assert not out.exists()


def test_schema_view_never_reports_a_schema_uri_as_a_contract_id() -> None:
    current = SchemaView({"$id": "https://schemas.example/record/v1"})
    legacy = SchemaView({"$id": "example.docs:Record/v1"})

    assert current.contract_id is None
    assert current.schema_id == "https://schemas.example/record/v1"
    assert legacy.contract_id == "example.docs:Record/v1"
    assert legacy.schema_id is None


@pytest.mark.parametrize(
    "schema_id", ["relative/schema", "https://SCHEMAS.example/root", "urn:Example:root"]
)
def test_structural_validation_rejects_invalid_root_schema_identity(
    schema_id: str, tmp_path: Path
) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        f'$schema: "https://json-schema.org/draft/2020-12/schema"\n$id: {schema_id}\ntype: object\n'
    )

    result = validate_structural({}, schema)

    assert not result.ok
    assert result.errors == [
        {
            "kind": "schema_invalid",
            "reason": "identity",
            "message": "compiled schema resource identity is invalid",
            "schema_path": "/$id",
            "detail": "invalid_root_id",
        }
    ]


def test_structural_validation_rejects_invalid_resource_registry_key(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text("type: object\n")

    result = validate_structural({}, schema, resources={"relative/resource": True})

    assert not result.ok
    assert result.errors[0]["reason"] == "identity"
    assert result.errors[0]["detail"] == "invalid_registry_key"


@pytest.mark.parametrize("case", _NESTED_RESOURCE_VECTORS["cases"], ids=lambda case: case["id"])
def test_nested_resource_identity_vectors(case: dict[str, Any], tmp_path: Path) -> None:
    schema = tmp_path / f"{case['id']}.schema.json"
    schema.write_text(json.dumps(case["schema"], ensure_ascii=False), encoding="utf-8")

    result = validate_structural(case["values"], schema, resources=case["resources"])

    assert _structural_output(result) == case["expected"]


@pytest.mark.parametrize("pointer", _NESTED_RESOURCE_VECTORS["schema_locations"])
def test_every_schema_bearing_keyword_participates_in_nested_identity(
    pointer: str, tmp_path: Path
) -> None:
    schema = tmp_path / "location.schema.json"
    schema.write_text(json.dumps(_schema_at_location(pointer)), encoding="utf-8")

    result = validate_structural({}, schema)

    assert result.errors == [
        {
            "kind": "schema_invalid",
            "reason": "identity",
            "message": "compiled schema resource identity is invalid",
            "schema_path": f"{pointer}/$id",
            "detail": "invalid_nested_id",
        }
    ]


def test_embedded_resources_count_toward_the_exact_resource_limit(tmp_path: Path) -> None:
    def schema_with_nested_resources(count: int) -> dict[str, Any]:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://schemas.example/root/",
            "$defs": {
                f"resource{index:03d}": {"$id": f"resource{index:03d}"} for index in range(count)
            },
            "type": "object",
        }

    schema = tmp_path / "resource-limit.schema.json"
    limits = replace(DEFAULT_VALIDATION_LIMITS, max_resources=256)
    schema.write_text(json.dumps(schema_with_nested_resources(255)), encoding="utf-8")
    assert validate_structural({}, schema, limits=limits).ok

    schema.write_text(json.dumps(schema_with_nested_resources(256)), encoding="utf-8")
    result = validate_structural({}, schema, limits=limits)
    assert result.errors == [
        {
            "kind": "schema_invalid",
            "reason": "value_domain",
            "message": "compiled schema contains a non-portable YAML value",
            "schema_path": "",
        }
    ]
