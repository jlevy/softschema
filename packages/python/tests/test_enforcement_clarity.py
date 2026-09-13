"""Execution evidence must describe actual independent payload checks."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, model_validator
from ruamel.yaml import YAML

from softschema.compile import compile_model
from softschema.models import Contract, SchemaProfile, SchemaStatus
from softschema.pipeline import repair_and_validate_artifact
from softschema.validate import validate_artifact, validate_values

VECTORS = Path(__file__).parents[3] / "tests/vectors/validation-execution.yaml"


class Sample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str

    @model_validator(mode="after")
    def accept_name(self) -> Sample:
        if self.name == "rejected":
            raise ValueError("name is unavailable")
        return self


def test_shared_validation_execution_vectors(tmp_path: Path) -> None:
    yaml = YAML(typ="safe")
    for case in yaml.load(VECTORS.read_text())["cases"]:
        directory = tmp_path / case["name"]
        directory.mkdir()
        doc = directory / "sample.yaml"
        with doc.open("w") as output:
            yaml.dump(case["values"], output)
        schema_path = None
        if "schema" in case or "schema_text" in case or case.get("missing_schema"):
            schema_path = directory / "sample.schema.yaml"
            if "schema_text" in case:
                schema_path.write_text(case["schema_text"])
            elif "schema" in case:
                with schema_path.open("w") as output:
                    yaml.dump(case["schema"], output)
        result = validate_artifact(
            doc,
            contract=Contract(
                id="example:Sample/v1",
                model=Sample if case.get("model") else None,
                schema_path=schema_path,
                status=SchemaStatus(case.get("status", "enforced")),
                profile=SchemaProfile.pure_yaml,
            ),
        )
        for layer in ("structural", "semantic"):
            expected = dict(case[layer])
            if isinstance(expected["execution"], dict):
                expected["execution"] = expected["execution"]["python"]
            actual = asdict(getattr(result, layer))
            assert {key: actual.get(key) for key in expected} == expected, case["name"]
        expected_ok = case["structural"]["ok"] and case["semantic"]["ok"]
        assert result.ok == expected_ok, case["name"]
        assert result.outcome == ("valid" if expected_ok else "invalid"), case["name"]
        assert result.warning_codes == ([case["warning"]] if "warning" in case else [])
        if "error_kind" in case:
            assert result.structural.errors[0]["kind"] == case["error_kind"], case["name"]
        assert "enforcement_applied" not in asdict(result)


def test_values_and_repair_preserve_independent_execution(tmp_path: Path) -> None:
    schema = tmp_path / "sample.schema.yaml"
    compile_model(Sample, schema, contract_id="example:Sample/v1")
    result = validate_values({"name": "rejected"}, schema=schema, model=Sample)
    assert result.structural.execution == result.semantic.execution == "completed"
    assert result.structural.ok
    assert not result.semantic.ok
    model_only = validate_values({"name": "hello"}, model=Sample)
    assert model_only.structural.execution == "not_run"
    assert model_only.structural.skipped_reason is None
    doc = tmp_path / "sample.yaml"
    doc.write_text("name: hello\n")
    repaired = repair_and_validate_artifact(
        doc,
        contract=Contract(
            id="example:Sample/v1",
            model=Sample,
            schema_path=schema,
            profile=SchemaProfile.pure_yaml,
        ),
        write=False,
    )
    assert repaired.structural.execution == repaired.semantic.execution == "completed"


def test_pre_payload_failure_runs_neither_check(tmp_path: Path) -> None:
    result = validate_artifact(
        tmp_path / "absent.md",
        contract=Contract(id="example:Sample/v1", model=Sample, status=SchemaStatus.enforced),
    )
    assert result.structural.execution == result.semantic.execution == "not_run"
    assert not result.ok
    assert not result.warnings


def test_semantic_programmer_exception_does_not_become_a_verdict() -> None:
    class BrokenModel(BaseModel):
        name: str

        @model_validator(mode="after")
        def fail(self) -> BrokenModel:
            raise TypeError("model implementation failed")

    with pytest.raises(TypeError, match="model implementation failed"):
        validate_values({"name": "hello"}, model=BrokenModel)
