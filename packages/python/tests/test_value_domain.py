from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from typing_extensions import override

from softschema import (
    DEFAULT_VALIDATION_LIMITS,
    Contract,
    SchemaProfile,
    SchemaStatus,
    ValidationLimits,
    validate_artifact,
    validate_structural,
)
from softschema.value_domain import (
    PortableValueError,
    normalize_portable_value,
    parse_portable_yaml,
)
from tests.yaml_fixtures import load_yaml_fixture

ROOT = Path(__file__).parents[3]
VECTORS = load_yaml_fixture(ROOT / "tests/value-domain/vectors.yaml")
JSON_SCHEMA_2020_12 = "https://json-schema.org/draft/2020-12/schema"


def _contract() -> Contract:
    return Contract(
        id="example:Value/v1",
        envelope_key="item",
        status=SchemaStatus.enforced,
    )


def test_shared_yaml_value_domain_vectors() -> None:
    for vector in VECTORS:
        if "value" in vector:
            assert parse_portable_yaml(vector["yaml"]) == vector["value"], vector["id"]
        else:
            with pytest.raises(PortableValueError) as caught:
                parse_portable_yaml(vector["yaml"])
            assert caught.value.path == vector["error_path"], vector["id"]
            if "line" in vector:
                assert caught.value.line == vector["line"], vector["id"]
                assert caught.value.column == vector["column"], vector["id"]


def test_default_validation_limits_are_the_portable_profile() -> None:
    assert (
        ValidationLimits(
            max_resource_bytes=8 * 1024 * 1024,
            max_bundle_bytes=64 * 1024 * 1024,
            max_resources=256,
            max_nodes_per_resource=100_000,
            max_depth=128,
            max_scalar_codepoints=1024 * 1024,
        )
        == DEFAULT_VALIDATION_LIMITS
    )


@pytest.mark.parametrize(
    ("yaml", "limits", "path"),
    [
        ("a: b\n", replace(DEFAULT_VALIDATION_LIMITS, max_resource_bytes=3), ""),
        ("a: b\n", replace(DEFAULT_VALIDATION_LIMITS, max_nodes_per_resource=2), "/a"),
        ("a: [b]\n", replace(DEFAULT_VALIDATION_LIMITS, max_depth=2), "/a/0"),
        ("a: two\n", replace(DEFAULT_VALIDATION_LIMITS, max_scalar_codepoints=2), "/a"),
    ],
)
def test_each_per_resource_limit_can_be_overridden(
    yaml: str,
    limits: ValidationLimits,
    path: str,
) -> None:
    with pytest.raises(PortableValueError) as caught:
        parse_portable_yaml(yaml, limits=limits)
    assert caught.value.path == path


def test_parser_rejects_adversarial_depth_before_python_recursion() -> None:
    yaml = "value: " + "[" * 5000 + "0" + "]" * 5000 + "\n"

    with pytest.raises(PortableValueError) as caught:
        parse_portable_yaml(yaml)

    assert caught.value.path.startswith("/value")


def test_default_byte_and_scalar_limits_reject_oversized_input() -> None:
    with pytest.raises(PortableValueError) as byte_error:
        parse_portable_yaml("x" * (DEFAULT_VALIDATION_LIMITS.max_resource_bytes + 1))
    assert byte_error.value.path == ""

    oversized_scalar = "x" * (DEFAULT_VALIDATION_LIMITS.max_scalar_codepoints + 1)
    with pytest.raises(PortableValueError) as scalar_error:
        parse_portable_yaml(f"value: {oversized_scalar}\n")
    assert scalar_error.value.path == "/value"


def test_materialized_resources_use_canonical_json_budgets(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        f"$schema: {JSON_SCHEMA_2020_12}\n$ref: https://schemas.example/value\n",
        encoding="utf-8",
    )
    resources: dict[str, Any] = {"https://schemas.example/value": True}
    root_size = len(schema.read_bytes())

    too_small = replace(DEFAULT_VALIDATION_LIMITS, max_bundle_bytes=root_size + 3)
    result = validate_structural({}, schema, resources=resources, limits=too_small)
    assert result.errors == [
        {
            "kind": "schema_invalid",
            "reason": "value_domain",
            "message": "compiled schema contains a non-portable YAML value",
            "schema_path": "",
        }
    ]

    exact = replace(DEFAULT_VALIDATION_LIMITS, max_bundle_bytes=root_size + 4)
    assert validate_structural({}, schema, resources=resources, limits=exact).ok is True


@pytest.mark.parametrize(
    ("value", "expected_size"),
    [
        ({"x": 0.00001}, 11),
        ({"x": "😀"}, 12),
        ({"x": 1.0}, 7),
        ({"z": False, "a": [None, 1.2345e-5]}, 33),
    ],
)
def test_canonical_json_size_is_portable(value: Any, expected_size: int) -> None:
    assert normalize_portable_value(value)[1] == expected_size


def test_total_resource_count_includes_the_root(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text(f"$schema: {JSON_SCHEMA_2020_12}\ntype: object\n", encoding="utf-8")
    resources = {"https://schemas.example/extra": True}
    limits = replace(DEFAULT_VALIDATION_LIMITS, max_resources=1)

    result = validate_structural({}, schema, resources=resources, limits=limits)

    assert result.errors[0]["reason"] == "value_domain"


def test_schema_and_artifact_boundaries_return_portable_value_domain_records(
    tmp_path: Path,
) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        f"$schema: {JSON_SCHEMA_2020_12}\ntype: object\nmaximum: 1e20\n",
        encoding="utf-8",
    )
    schema_result = validate_structural({}, schema)
    assert schema_result.errors == [
        {
            "kind": "schema_invalid",
            "reason": "value_domain",
            "message": "compiled schema contains a non-portable YAML value",
            "schema_path": "/maximum",
        }
    ]

    artifact = tmp_path / "artifact.md"
    artifact.write_text(
        "---\nsoftschema:\n  contract: example:Value/v1\nitem:\n  value: .nan\n---\n",
        encoding="utf-8",
    )
    artifact_result = validate_artifact(artifact, contract=_contract())
    assert artifact_result.structural.errors == [
        {
            "kind": "parse_error",
            "reason": "value_domain",
            "message": "artifact contains a non-portable YAML value",
            "source": str(artifact),
            "path": "/item/value",
        }
    ]

    pure_artifact = tmp_path / "artifact.yaml"
    pure_artifact.write_text("item:\n  value: .nan\n", encoding="utf-8")
    pure_contract = Contract(
        id="example:Value/v1",
        envelope_key="item",
        status=SchemaStatus.enforced,
        profile=SchemaProfile.pure_yaml,
    )
    pure_result = validate_artifact(pure_artifact, contract=pure_contract)
    assert pure_result.structural.errors[0]["reason"] == "value_domain"
    assert pure_result.structural.errors[0]["path"] == "/item/value"


def test_materialized_values_reject_cycles_non_json_types_and_negative_zero(
    tmp_path: Path,
) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        f"$schema: {JSON_SCHEMA_2020_12}\n$ref: https://schemas.example/value\n",
        encoding="utf-8",
    )
    cyclic: dict[str, Any] = {}
    cyclic["self"] = cyclic
    for resource in (cyclic, {"value": object()}, {"value": 9007199254740992}):
        result = validate_structural(
            {}, schema, resources={"https://schemas.example/value": resource}
        )
        assert result.errors[0]["reason"] == "value_domain"

    normalized = {
        "$schema": JSON_SCHEMA_2020_12,
        "const": -0.0,
    }
    result = validate_structural(
        0,
        schema,
        resources={"https://schemas.example/value": normalized},
    )
    assert result.ok is True


def test_materialized_mapping_failures_use_unicode_scalar_order() -> None:
    value = {"😀": object(), "\ue000": object()}
    with pytest.raises(PortableValueError) as caught:
        normalize_portable_value(value)
    assert caught.value.path == "/\ue000"

    valid = {"😀": 1, "\ue000": 2}
    normalized, _ = normalize_portable_value(valid)
    assert isinstance(normalized, dict)
    assert list(normalized) == list(valid)


def test_materialized_non_string_keys_are_not_coerced() -> None:
    class HostileKey:
        @override
        def __str__(self) -> str:
            raise AssertionError("key coercion must not run")

    with pytest.raises(PortableValueError, match="mapping keys must be strings"):
        normalize_portable_value({HostileKey(): True})
