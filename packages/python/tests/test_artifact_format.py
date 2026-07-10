from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from softschema import (
    ARTIFACT_FORMAT_VERSION,
    Contract,
    SchemaMetadata,
    parse_schema_metadata,
    validate_artifact,
    validate_extension_namespace,
)

ROOT = Path(__file__).parents[3]
VECTORS: list[dict[str, Any]] = json.loads(
    (ROOT / "tests/parity/artifact-format.json").read_text(encoding="utf-8")
)


def test_artifact_format_public_api_is_explicit_and_versioned() -> None:
    assert ARTIFACT_FORMAT_VERSION == "1"
    assert validate_extension_namespace("com.example.review") == "com.example.review"


def test_python_model_validation_keeps_idiomatic_field_names() -> None:
    metadata = SchemaMetadata.model_validate(
        {
            "contract_id": "example.docs:Record/v1",
            "format_version": "1",
            "extensions": {"com.example.review": {"ready": True}},
        }
    )

    assert metadata.model_dump(by_alias=True) == {
        "contract": "example.docs:Record/v1",
        "schema": None,
        "envelope": None,
        "status": None,
        "format": "1",
        "extensions": {"com.example.review": {"ready": True}},
    }


@pytest.mark.parametrize("vector", VECTORS, ids=lambda vector: vector["id"])
def test_artifact_format_vectors(vector: dict[str, Any]) -> None:
    if vector.get("error"):
        with pytest.raises((ValueError, ValidationError)):
            parse_schema_metadata(vector["raw"])
        return

    metadata = parse_schema_metadata(vector["raw"])

    assert metadata is not None
    assert metadata.model_dump(by_alias=True) == vector["output"]


def test_format_1_extensions_round_trip_through_artifact_validation(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.md"
    artifact.write_text(
        "---\n"
        "softschema:\n"
        '  format: "1"\n'
        "  contract: example.docs:Record/v1\n"
        "  extensions:\n"
        "    com.example.review:\n"
        "      labels: [ready, 2, null]\n"
        "record:\n"
        "  title: Example\n"
        "---\n",
        encoding="utf-8",
    )

    result = validate_artifact(
        artifact,
        contract=Contract(id="example.docs:Record/v1", envelope_key="record"),
    )

    assert result.ok is True
    assert result.document_metadata is not None
    assert result.document_metadata.model_dump(by_alias=True)["extensions"] == {
        "com.example.review": {"labels": ["ready", 2, None]}
    }


def test_duplicate_extension_namespaces_fail_at_the_portable_yaml_boundary(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "duplicate-extension.md"
    artifact.write_text(
        "---\n"
        "softschema:\n"
        '  format: "1"\n'
        "  contract: example.docs:Record/v1\n"
        "  extensions:\n"
        "    com.example.review: first\n"
        "    com.example.review: second\n"
        "record:\n"
        "  title: Example\n"
        "---\n",
        encoding="utf-8",
    )

    result = validate_artifact(
        artifact,
        contract=Contract(id="example.docs:Record/v1", envelope_key="record"),
    )

    assert result.structural.errors == [
        {
            "kind": "parse_error",
            "reason": "value_domain",
            "message": "artifact contains a non-portable YAML value",
            "source": str(artifact),
            "path": "/softschema/extensions/com.example.review",
        }
    ]


def test_materialized_extension_values_must_be_portable() -> None:
    cyclic: dict[str, Any] = {}
    cyclic["self"] = cyclic

    with pytest.raises(ValueError, match="cycles are not portable"):
        parse_schema_metadata(
            {
                "format": "1",
                "contract": "example.docs:Record/v1",
                "extensions": {"com.example.review": cyclic},
            }
        )
