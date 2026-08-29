"""Repair and conform, driven by the shared vectors.

The vectors own the *rules* — which documents repair, which conform, which are
deliberately left alone. This module runs them and adds the handful of cases the shared
corpus cannot carry: the filesystem boundary, and the semantic (Pydantic) conform source,
which is per-language by design.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from ruamel.yaml import YAML

from softschema.conform import conform_artifact
from softschema.models import Contract, SchemaProfile
from softschema.pipeline import repair_and_validate_artifact
from softschema.repair import repair_artifact

HARDENING_VECTORS = Path(__file__).resolve().parents[3] / "tests/vectors/hardening.yaml"


def _vectors(name: str) -> list[dict[str, Any]]:
    return YAML(typ="safe").load(HARDENING_VECTORS.read_text())[name]


def _write(path: Path, text: str) -> None:
    """Write a fixture without letting Python's newline translation touch it."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _read(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


@pytest.mark.parametrize("case", _vectors("yaml_repair"), ids=lambda case: case["id"])
def test_yaml_repair_vectors(case: dict[str, Any], tmp_path: Path) -> None:
    profile = SchemaProfile(case["profile"])
    suffix = ".yaml" if profile is SchemaProfile.pure_yaml else ".md"
    path = tmp_path / f"artifact{suffix}"
    _write(path, case["text"])

    result = repair_artifact(path, profile=profile, write=True)

    assert result.changed is case["repaired"]
    if case["repaired"]:
        assert _read(path) == case["expected_text"]
    else:
        # Whatever the reason, an unrepaired document is left exactly as it was found.
        assert _read(path) == case["text"]
        if "code" in case:
            assert result.error_code == case["code"]


@pytest.mark.parametrize("case", _vectors("schema_conform"), ids=lambda case: case["id"])
def test_schema_conform_vectors(case: dict[str, Any], tmp_path: Path) -> None:
    path = tmp_path / "artifact.md"
    _write(path, case["text"])
    schema_path = tmp_path / "schema.yaml"
    YAML(typ="safe").dump(case["schema"], schema_path.open("w", encoding="utf-8"))

    result = conform_artifact(
        path, schema_path=schema_path, envelope_key=case["envelope"], write=True
    )

    assert result.changed is case["changed"]
    assert _read(path) == case.get("expected_text", case["text"])


def test_repair_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "a.md"
    _write(path, "---\nthing:\n  summary: Note: actually Q1\n---\nBody.\n")

    repair_artifact(path, profile=SchemaProfile.frontmatter_md, write=True)
    once = _read(path)
    repair_artifact(path, profile=SchemaProfile.frontmatter_md, write=True)

    assert _read(path) == once


def test_check_mode_never_writes(tmp_path: Path) -> None:
    path = tmp_path / "a.md"
    original = "---\nthing:\n  summary: Note: actually Q1\n---\nBody.\n"
    _write(path, original)

    result = repair_artifact(path, profile=SchemaProfile.frontmatter_md, write=False)

    assert result.changed is True
    assert _read(path) == original


def test_unwritable_path_is_reported_not_raised(tmp_path: Path) -> None:
    missing = tmp_path / "nope.md"

    result = repair_artifact(missing, profile=SchemaProfile.frontmatter_md)

    assert result.ok is False
    assert result.error_code == "artifact_unreadable"


class _Thing(BaseModel):
    name: str


def test_conform_fires_for_a_model_only_contract(tmp_path: Path) -> None:
    """A contract with a model and no schema path still conforms.

    This is the regression guard for the case that motivated reading both validation
    layers. A host registering contracts as Pydantic models binds no compiled schema, so
    the structural layer reports ``skipped_reason="no_schema"`` and a conform keyed only on
    it would silently do nothing.
    """
    path = tmp_path / "a.md"
    _write(path, "---\nthing:\n  name: 1850\n---\nBody.\n")

    result = conform_artifact(path, model=_Thing, envelope_key="thing", write=True)

    assert result.changed is True
    assert _read(path) == "---\nthing:\n  name: '1850'\n---\nBody.\n"


def test_conform_without_any_binding_says_so(tmp_path: Path) -> None:
    """No schema and no model is "nothing to conform against", not a silent success."""
    path = tmp_path / "a.md"
    _write(path, "---\nthing:\n  name: 1850\n---\nBody.\n")

    result = conform_artifact(path, envelope_key="thing", write=True)

    assert result.changed is False
    assert result.skipped_reason == "no_contract_binding"


def test_pipeline_writes_once_and_reports_both_passes(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.yaml"
    schema_path.write_text(
        "type: object\nrequired: [name, summary]\n"
        "properties:\n  name: {type: string}\n  summary: {type: string}\n"
    )
    path = tmp_path / "a.md"
    _write(path, "---\nthing:\n  name: 1850\n  summary: Note: actually Q1\n---\nBody.\n")
    contract = Contract(id="test:Thing", envelope_key="thing", schema_path=schema_path)

    result = repair_and_validate_artifact(path, contract=contract, write=True)

    assert result.outcome == "valid"
    assert [record["code"] for record in result.repairs] == [
        "yaml_quoted_scalar",
        "scalar_conformed",
    ]
    assert _read(path) == (
        "---\nthing:\n  name: '1850'\n  summary: \"Note: actually Q1\"\n---\nBody.\n"
    )


def test_pipeline_leaves_a_valid_document_byte_identical(tmp_path: Path) -> None:
    """The no-widening invariant, at the level a caller sees it."""
    schema_path = tmp_path / "schema.yaml"
    schema_path.write_text("type: object\nproperties:\n  name: {type: string}\n")
    path = tmp_path / "a.md"
    original = "---\nthing:\n  name: 'fine'   # spaced comment\n---\nBody.\n"
    _write(path, original)
    contract = Contract(id="test:Thing", envelope_key="thing", schema_path=schema_path)

    result = repair_and_validate_artifact(path, contract=contract, write=True)

    assert result.repairs == []
    assert _read(path) == original


def test_pipeline_does_not_invent_a_missing_field(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.yaml"
    schema_path.write_text(
        "type: object\nrequired: [rationale]\nproperties:\n  rationale: {type: string}\n"
    )
    path = tmp_path / "a.md"
    _write(path, "---\nthing:\n  reason: because\n---\nBody.\n")
    contract = Contract(id="test:Thing", envelope_key="thing", schema_path=schema_path)

    result = repair_and_validate_artifact(path, contract=contract, write=True)

    assert result.outcome == "invalid"
    assert result.repairs == []
    # The near-miss key is reported, never renamed.
    assert _read(path) == "---\nthing:\n  reason: because\n---\nBody.\n"
    assert [error["code"] for error in result.structural.errors] == ["missing_property"]
