from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from softschema import (
    DEFAULT_VALIDATION_LIMITS,
    Contract,
    SchemaProfile,
    artifact_error_record,
    read_frontmatter,
    validate_artifact,
)
from softschema.cli import main as softschema_main
from softschema.value_domain import PortableValueError, PortableYamlSyntaxError
from tests.yaml_fixtures import load_yaml_fixture

ROOT = Path(__file__).parents[3]
VECTORS: list[dict[str, Any]] = load_yaml_fixture(ROOT / "tests/parity/artifact-input.yaml")
MESSAGES = {
    "not_found": "artifact path does not exist",
    "unreadable": "artifact path cannot be read",
    "directory_requires_recursive": "artifact directory requires --recursive",
}


def _contract(profile: str) -> Contract:
    return Contract(id="example:Value/v1", profile=SchemaProfile(profile))


@pytest.mark.parametrize("vector", VECTORS, ids=lambda vector: vector["id"])
def test_artifact_parse_vectors_are_stable(tmp_path: Path, vector: dict[str, Any]) -> None:
    suffix = ".md" if vector["profile"] == "frontmatter-md" else ".yaml"
    artifact = tmp_path / f"artifact{suffix}"
    artifact.write_text(vector["content"], encoding="utf-8")

    result = validate_artifact(artifact, contract=_contract(vector["profile"]))

    expected = {
        "kind": "parse_error",
        "reason": vector["reason"],
        "message": vector["message"],
        "source": str(artifact),
    }
    if "path" in vector:
        expected["path"] = vector["path"]
    assert result.structural.errors == [expected]
    assert result.semantic.skipped_reason == "parse_error"


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("missing.md", "not_found"),
        ("directory", "directory_requires_recursive"),
    ],
)
def test_artifact_access_records_are_stable(tmp_path: Path, name: str, reason: str) -> None:
    source = tmp_path / name
    if reason == "directory_requires_recursive":
        source.mkdir()

    result = validate_artifact(source, contract=_contract("frontmatter-md"))

    assert result.structural.errors == [
        {
            "kind": "input_error",
            "reason": reason,
            "message": MESSAGES[reason],
            "source": str(source),
        }
    ]
    assert result.semantic.skipped_reason == "input_error"


@pytest.mark.parametrize(
    ("vector_id", "expected_exit"),
    [
        ("frontmatter-delimiter", 1),
        ("frontmatter-syntax", 1),
        ("frontmatter-list-root", 1),
        ("frontmatter-value-domain", 1),
        ("pure-yaml-syntax", 1),
        ("pure-yaml-list-root", 1),
    ],
)
def test_validate_cli_emits_discriminated_parse_records(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    vector_id: str,
    expected_exit: int,
) -> None:
    vector = next(item for item in VECTORS if item["id"] == vector_id)
    suffix = ".md" if vector["profile"] == "frontmatter-md" else ".yaml"
    source = tmp_path / f"artifact{suffix}"
    source.write_text(vector["content"], encoding="utf-8")

    exit_code = softschema_main(
        [
            "validate",
            str(source),
            "--profile",
            vector["profile"],
            "--contract",
            "example:Value/v1",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == expected_exit
    assert captured.err == ""
    record = json.loads(captured.out)
    assert record["kind"] == "parse_error"
    assert record["reason"] == vector["reason"]
    assert record["message"] == vector["message"]
    assert record["source"] == str(source)
    assert "line" not in record
    assert "column" not in record


def test_validate_cli_emits_input_error_and_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "missing.md"

    exit_code = softschema_main(["validate", str(source), "--contract", "example:Value/v1"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "kind": "input_error",
        "reason": "not_found",
        "message": "artifact path does not exist",
        "source": str(source),
    }


def test_artifact_error_normalizer_retains_locations_for_diagnostics(tmp_path: Path) -> None:
    source = tmp_path / "syntax.md"
    source.write_text("---\nitem: [unclosed\n---\n", encoding="utf-8")

    with pytest.raises(PortableYamlSyntaxError) as caught:
        read_frontmatter(source)

    record = artifact_error_record(source, caught.value, include_location=True)
    assert record is not None
    assert record["reason"] == "syntax"
    assert record["line"] == 3
    assert record["column"] == 1


def test_frontmatter_limit_locations_include_the_document_offset(tmp_path: Path) -> None:
    source = tmp_path / "limit.md"
    source.write_text("---\nx: too\n---\n", encoding="utf-8")
    limits = replace(DEFAULT_VALIDATION_LIMITS, max_scalar_codepoints=2)

    with pytest.raises(PortableValueError) as caught:
        read_frontmatter(source, limits)

    assert (caught.value.path, caught.value.line, caught.value.column) == ("/x", 2, 4)


def test_artifact_error_normalizer_covers_unreadable_and_invalid_utf8(tmp_path: Path) -> None:
    source = tmp_path / "artifact.md"
    assert artifact_error_record(source, PermissionError()) == {
        "kind": "input_error",
        "reason": "unreadable",
        "message": "artifact path cannot be read",
        "source": str(source),
    }

    source.write_bytes(b"---\nitem: \xff\n---\n")
    result = validate_artifact(source, contract=_contract("frontmatter-md"))
    assert result.structural.errors == [
        {
            "kind": "parse_error",
            "reason": "syntax",
            "message": "artifact is not valid YAML",
            "source": str(source),
        }
    ]
