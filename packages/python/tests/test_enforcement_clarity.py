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
from softschema.validate import (
    ArtifactInvalidError,
    load_artifact,
    validate_artifact,
    validate_values,
)

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
            require=case.get("require", ()),
        )
        for layer in ("structural", "semantic"):
            expected = dict(case[layer])
            if isinstance(expected["execution"], dict):
                expected["execution"] = expected["execution"]["python"]
            actual = asdict(getattr(result, layer))
            assert {key: actual.get(key) for key in expected} == expected, case["name"]
            unmet = [
                {key: error.get(key) for key in ("kind", "layer", "execution")}
                for error in actual["errors"]
                if error.get("kind") == "check_not_completed"
            ]
            required = layer in case.get("require", ()) and expected["execution"] != "completed"
            assert unmet == (
                [
                    {
                        "kind": "check_not_completed",
                        "layer": layer,
                        "execution": expected["execution"],
                    }
                ]
                if required
                else []
            ), case["name"]
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


def _sample_contract(
    tmp_path: Path, *, schema_path: Path | None = None, model: type[BaseModel] | None = None
) -> tuple[Path, Contract]:
    doc = tmp_path / "sample.yaml"
    doc.write_text("name: hello\n")
    contract = Contract(
        id="example:Sample/v1",
        model=model,
        schema_path=schema_path,
        status=SchemaStatus.enforced,
        profile=SchemaProfile.pure_yaml,
    )
    return doc, contract


def test_required_structural_check_completed_by_bound_schema_stays_valid(tmp_path: Path) -> None:
    schema = tmp_path / "sample.schema.yaml"
    compile_model(Sample, schema, contract_id="example:Sample/v1")
    doc, contract = _sample_contract(tmp_path, schema_path=schema)
    result = validate_artifact(doc, contract=contract, require=["structural"])
    assert result.outcome == "valid"
    assert result.structural.execution == "completed"
    assert result.structural.errors == []
    assert result == validate_artifact(doc, contract=contract)
    assert load_artifact(doc, contract=contract, require=["structural"]) == {"name": "hello"}


def test_required_semantic_check_without_model_is_invalid(tmp_path: Path) -> None:
    doc, contract = _sample_contract(tmp_path)
    assert validate_artifact(doc, contract=contract).outcome == "valid"
    result = validate_artifact(doc, contract=contract, require=["semantic"])
    assert result.outcome == "invalid"
    assert result.structural == validate_artifact(doc, contract=contract).structural
    assert not result.semantic.ok
    assert result.semantic.execution == "not_run"
    assert result.semantic.skipped_reason == "no_semantic_model"
    assert result.semantic.errors == [
        {
            "kind": "check_not_completed",
            "message": "required semantic check did not complete (execution: not_run)",
            "layer": "semantic",
            "execution": "not_run",
        }
    ]
    with pytest.raises(ArtifactInvalidError) as raised:
        load_artifact(doc, contract=contract, require=["semantic"])
    assert raised.value.result == result


def test_required_check_preserves_schema_preparation_error(tmp_path: Path) -> None:
    schema = tmp_path / "sample.schema.yaml"
    schema.write_text("[")
    doc, contract = _sample_contract(tmp_path, schema_path=schema, model=Sample)
    unrequired = validate_artifact(doc, contract=contract)
    result = validate_artifact(doc, contract=contract, require=["structural", "semantic"])
    assert result.outcome == "invalid"
    assert result.structural.execution == "not_run"
    assert result.structural.errors[0] == unrequired.structural.errors[0]
    assert result.structural.errors[0]["kind"] == "schema_invalid"
    assert result.structural.errors[1] == {
        "kind": "check_not_completed",
        "message": "required structural check did not complete (execution: not_run)",
        "layer": "structural",
        "execution": "not_run",
    }
    assert result.semantic == unrequired.semantic
    assert result.warnings == unrequired.warnings


def test_required_check_keeps_pre_payload_input_error(tmp_path: Path) -> None:
    _doc, contract = _sample_contract(tmp_path)
    result = validate_artifact(tmp_path / "absent.yaml", contract=contract, require=["structural"])
    assert result.outcome == "input_error"
    assert result.structural.errors[0]["kind"] == "artifact_unreadable"
    assert result.structural.errors[-1]["kind"] == "check_not_completed"


def test_required_checks_on_values(tmp_path: Path) -> None:
    schema = tmp_path / "sample.schema.yaml"
    compile_model(Sample, schema, contract_id="example:Sample/v1")
    both = validate_values({"name": "hello"}, schema=schema, model=Sample)
    assert (
        validate_values(
            {"name": "hello"}, schema=schema, model=Sample, require=("structural", "semantic")
        )
        == both
    )
    model_only = validate_values({"name": "hello"}, model=Sample, require=["structural"])
    assert not model_only.ok
    assert model_only.structural.errors[-1]["kind"] == "check_not_completed"
    assert model_only.semantic.ok


def test_require_rejects_unknown_layer(tmp_path: Path) -> None:
    doc, contract = _sample_contract(tmp_path)
    with pytest.raises(ValueError, match="payload"):
        validate_artifact(doc, contract=contract, require=["payload"])  # pyright: ignore[reportArgumentType]
