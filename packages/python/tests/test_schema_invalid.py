from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from softschema import validate_structural, validate_values

JSON_SCHEMA_2020_12 = "https://json-schema.org/draft/2020-12/schema"


class NameModel(BaseModel):
    name: str


def _write_schema(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_malformed_schema_syntax_and_roots_return_stable_records(tmp_path: Path) -> None:
    cases = [
        (
            "properties: [\n",
            {
                "kind": "schema_invalid",
                "reason": "syntax",
                "message": "compiled schema is not valid YAML or JSON",
                "schema_path": "",
            },
        ),
        (
            "null\n",
            {
                "kind": "schema_invalid",
                "reason": "root",
                "message": "compiled schema root must be a mapping",
                "schema_path": "",
            },
        ),
        (
            "- one\n- two\n",
            {
                "kind": "schema_invalid",
                "reason": "root",
                "message": "compiled schema root must be a mapping",
                "schema_path": "",
            },
        ),
        (
            "scalar\n",
            {
                "kind": "schema_invalid",
                "reason": "root",
                "message": "compiled schema root must be a mapping",
                "schema_path": "",
            },
        ),
    ]

    for index, (text, expected) in enumerate(cases):
        schema = _write_schema(tmp_path / f"root-{index}.schema.yaml", text)
        result = validate_structural({"name": "Ada"}, schema)
        assert result.ok is False
        assert result.errors == [expected]


def test_schema_dialect_metaschema_compile_and_reference_failures_are_stable(
    tmp_path: Path,
) -> None:
    cases = [
        (
            "$schema: http://json-schema.org/draft-07/schema#\ntype: object\n",
            {
                "kind": "schema_invalid",
                "reason": "dialect",
                "message": "compiled schema uses an unsupported JSON Schema dialect",
                "schema_path": "/$schema",
                "dialect": "http://json-schema.org/draft-07/schema#",
            },
        ),
        (
            "$schema: 42\ntype: object\n",
            {
                "kind": "schema_invalid",
                "reason": "metaschema",
                "message": "compiled schema does not conform to Draft 2020-12",
                "schema_path": "/$schema",
            },
        ),
        (
            f"$schema: {JSON_SCHEMA_2020_12}\ntype: 42\n",
            {
                "kind": "schema_invalid",
                "reason": "metaschema",
                "message": "compiled schema does not conform to Draft 2020-12",
                "schema_path": "/type",
            },
        ),
        (
            (f"$schema: {JSON_SCHEMA_2020_12}\n$defs:\n  a/b~c:\n    type: 42\ntype: object\n"),
            {
                "kind": "schema_invalid",
                "reason": "metaschema",
                "message": "compiled schema does not conform to Draft 2020-12",
                "schema_path": "/$defs/a~1b~0c/type",
            },
        ),
        (
            f"$schema: {JSON_SCHEMA_2020_12}\ntype: string\npattern: '['\n",
            {
                "kind": "schema_invalid",
                "reason": "compile",
                "message": "compiled schema could not be compiled",
                "schema_path": "/pattern",
            },
        ),
        (
            (
                f"$schema: {JSON_SCHEMA_2020_12}\n"
                "$defs:\n"
                "  cycle: &cycle\n"
                "    type: object\n"
                "    properties:\n"
                "      child: *cycle\n"
                "type: object\n"
            ),
            {
                "kind": "schema_invalid",
                "reason": "compile",
                "message": "compiled schema could not be compiled",
                "schema_path": "/$defs/cycle/properties/child",
            },
        ),
        (
            f"$schema: {JSON_SCHEMA_2020_12}\n$ref: https://schemas.example/missing\n",
            {
                "kind": "schema_invalid",
                "reason": "reference",
                "message": "compiled schema reference is unavailable offline",
                "schema_path": "/$ref",
                "reference": "https://schemas.example/missing",
            },
        ),
        (
            f"$schema: {JSON_SCHEMA_2020_12}\n$ref: '#/$defs/missing'\n",
            {
                "kind": "schema_invalid",
                "reason": "reference",
                "message": "compiled schema reference is unavailable offline",
                "schema_path": "/$ref",
                "reference": "#/$defs/missing",
            },
        ),
    ]

    for index, (text, expected) in enumerate(cases):
        schema = _write_schema(tmp_path / f"invalid-{index}.schema.yaml", text)
        result = validate_structural({"name": "Ada"}, schema)
        assert result.ok is False
        assert result.errors == [expected]


def test_legacy_identity_and_supplied_resources_use_the_same_loader(tmp_path: Path) -> None:
    legacy = _write_schema(
        tmp_path / "legacy.schema.yaml",
        (
            f"$schema: {JSON_SCHEMA_2020_12}\n"
            "$id: example:Name/v1\n"
            "type: object\n"
            "properties:\n"
            "  name:\n"
            "    type: string\n"
            "x-softschema:\n"
            "  contract: example:Name/v1\n"
        ),
    )
    assert validate_structural({"name": "Ada"}, legacy).ok is True

    mismatched = _write_schema(
        tmp_path / "legacy-mismatch.schema.yaml",
        (
            f"$schema: {JSON_SCHEMA_2020_12}\n"
            "$id: example:Wrong/v1\n"
            "type: object\n"
            "x-softschema:\n"
            "  contract: example:Name/v1\n"
        ),
    )
    mismatch_result = validate_structural({}, mismatched)
    assert mismatch_result.errors == [
        {
            "kind": "schema_invalid",
            "reason": "profile",
            "message": "compiled schema is outside the softschema profile",
            "schema_path": "/$id",
            "detail": "legacy_contract_id_mismatch",
        }
    ]

    root = _write_schema(
        tmp_path / "resource-root.schema.yaml",
        f"$schema: {JSON_SCHEMA_2020_12}\n$ref: https://schemas.example/name\n",
    )
    resources = {
        "https://schemas.example/name": {
            "$schema": JSON_SCHEMA_2020_12,
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        }
    }
    assert validate_structural({"name": "Ada"}, root, resources=resources).ok is True

    invalid_resources = {
        "https://schemas.example/name": {
            "$schema": JSON_SCHEMA_2020_12,
            "type": 42,
        }
    }
    invalid_result = validate_structural({}, root, resources=invalid_resources)
    assert invalid_result.errors == [
        {
            "kind": "schema_invalid",
            "reason": "metaschema",
            "message": "compiled schema does not conform to Draft 2020-12",
            "schema_path": "/type",
        }
    ]

    mismatched_resources = {
        "https://schemas.example/name": {
            "$schema": JSON_SCHEMA_2020_12,
            "$id": "https://schemas.example/other",
            "type": "object",
        }
    }
    identity_result = validate_structural({}, root, resources=mismatched_resources)
    assert identity_result.errors == [
        {
            "kind": "schema_invalid",
            "reason": "identity",
            "message": "compiled schema resource identity is invalid",
            "schema_path": "/$id",
            "detail": "resource_id_mismatch",
        }
    ]


def test_semantic_validation_runs_when_the_compiled_schema_is_invalid(tmp_path: Path) -> None:
    schema = _write_schema(tmp_path / "bad.schema.yaml", "type: 42\n")

    result = validate_values({"name": "Ada"}, model=NameModel, schema=schema)

    assert result.structural.ok is False
    assert result.semantic.ok is True
