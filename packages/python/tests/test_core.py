from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, model_validator

from softschema import (
    Contract,
    Contracts,
    SchemaProfile,
    SchemaStatus,
    compile_model,
    validate_artifact,
    validate_semantic,
    validate_structural,
    validate_values,
)


class SampleModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    direction: str
    delta: float

    @model_validator(mode="after")
    def direction_matches_delta(self) -> SampleModel:
        if self.direction == "up" and self.delta < 0:
            raise ValueError(f"direction=up but delta={self.delta}")
        if self.direction == "down" and self.delta > 0:
            raise ValueError(f"direction=down but delta={self.delta}")
        return self


class EnvelopeModel(BaseModel):
    sample: SampleModel


def test_compile_writes_json_schema_with_contract_id(tmp_path: Path) -> None:
    out = tmp_path / "sample.schema.yaml"

    result = compile_model(SampleModel, out, contract_id="example:Sample/v1")

    assert out.is_file()
    assert "$schema:" in result.schema_yaml
    assert "$id: example:Sample/v1" in result.schema_yaml
    assert "schema_sha256" in result.schema_yaml
    assert result.schema_sha256 is not None


def test_validate_structural_and_semantic(tmp_path: Path) -> None:
    schema_path = tmp_path / "sample.schema.yaml"
    compile_model(SampleModel, schema_path, contract_id="example:Sample/v1")
    values = {"name": "hello", "direction": "up", "delta": 1.5}

    assert validate_structural(values, schema_path).ok
    assert validate_semantic(values, SampleModel).ok
    combined = validate_values(values, model=SampleModel, schema=schema_path)
    assert combined.structural.ok
    assert combined.semantic.ok


def test_validate_semantic_runs_cross_field_invariant() -> None:
    result = validate_semantic({"name": "hello", "direction": "up", "delta": -1.0}, SampleModel)

    assert not result.ok
    assert any("direction=up" in str(error.get("msg", "")) for error in result.errors)


def test_validate_values_requires_a_model_or_schema() -> None:
    with pytest.raises(ValueError, match="model="):
        validate_values({"name": "hello"})


def test_validate_artifact_without_envelope_key_uses_frontmatter_root(tmp_path: Path) -> None:
    schema_path = tmp_path / "sample.schema.yaml"
    compile_model(SampleModel, schema_path, contract_id="example:Sample/v1")
    doc = tmp_path / "doc.md"
    write_doc(doc, "name: hello\ndirection: up\ndelta: 1.5\n")
    contract = Contract(
        id="example:Sample/v1",
        model=SampleModel,
        schema_path=schema_path,
    )

    result = validate_artifact(doc, contract=contract)

    assert result.ok
    assert result.values == {"name": "hello", "direction": "up", "delta": 1.5}


def test_validate_artifact_reports_non_mapping_envelope(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    write_doc(doc, "sample:\n  - not\n  - a\n  - mapping\n")
    contract = Contract(id="example:Sample/v1", model=SampleModel, envelope_key="sample")

    result = validate_artifact(doc, contract=contract)

    assert not result.ok
    assert result.structural.errors[0]["kind"] == "envelope_not_mapping"


def test_validate_artifact_uses_contract_metadata_and_envelope(tmp_path: Path) -> None:
    doc = tmp_path / "sample.md"
    write_doc(
        doc,
        """
        softschema:
          contract: example:Sample/v1
          status: enforced
        sample:
          name: hello
          direction: up
          delta: 1.5
        """,
    )
    contract = Contract(
        id="example:Sample/v1",
        model=SampleModel,
        envelope_key="sample",
        status=SchemaStatus.enforced,
    )

    result = validate_artifact(doc, contract=contract)

    assert result.ok
    assert result.contract_id == "example:Sample/v1"
    assert result.values == {"name": "hello", "direction": "up", "delta": 1.5}


def test_validate_artifact_accepts_pure_yaml(tmp_path: Path) -> None:
    doc = tmp_path / "sample.yaml"
    doc.write_text("name: hello\ndirection: up\ndelta: 1.5\n")
    contract = Contract(
        id="example:Sample/v1",
        model=SampleModel,
        profile=SchemaProfile.pure_yaml,
        status=SchemaStatus.enforced,
    )

    result = validate_artifact(doc, contract=contract)

    assert result.ok
    assert result.profile == SchemaProfile.pure_yaml
    assert result.values == {"name": "hello", "direction": "up", "delta": 1.5}


def test_validate_artifact_rejects_contract_mismatch(tmp_path: Path) -> None:
    doc = tmp_path / "sample.md"
    write_doc(
        doc,
        """
        softschema:
          contract: other:Sample/v1
        sample:
          name: hello
          direction: up
          delta: 1.5
        """,
    )
    contract = Contract(id="example:Sample/v1", model=SampleModel, envelope_key="sample")

    result = validate_artifact(doc, contract=contract)

    assert not result.ok
    assert result.structural.errors[0]["kind"] == "document_contract_mismatch"


def test_validate_artifact_rejects_invalid_metadata(tmp_path: Path) -> None:
    doc = tmp_path / "sample.md"
    write_doc(
        doc,
        """
        softschema:
          status: enforced
        sample:
          name: hello
          direction: up
          delta: 1.5
        """,
    )
    contract = Contract(id="example:Sample/v1", model=SampleModel, envelope_key="sample")

    result = validate_artifact(doc, contract=contract)

    assert not result.ok
    assert result.structural.errors[0]["kind"] == "document_softschema_invalid"


def test_validate_artifact_reports_parse_error_for_malformed_pure_yaml(tmp_path: Path) -> None:
    doc = tmp_path / "bad.yaml"
    doc.write_text("key: [unclosed\n  : : :\n")
    contract = Contract(id="example:Sample/v1", profile=SchemaProfile.pure_yaml)

    result = validate_artifact(doc, contract=contract)

    assert not result.ok
    assert result.structural.errors[0]["kind"] == "parse_error"


def test_validate_artifact_reports_envelope_mismatch(tmp_path: Path) -> None:
    doc = tmp_path / "sample.md"
    write_doc(doc, "wrong:\n  name: hello\n  direction: up\n  delta: 1.5\n")
    contract = Contract(id="example:Sample/v1", model=SampleModel, envelope_key="sample")

    result = validate_artifact(doc, contract=contract)

    assert not result.ok
    assert result.structural.errors[0]["kind"] == "envelope_mismatch"


def test_validate_artifact_resolves_schema_path_relative_to_doc(tmp_path: Path) -> None:
    schema_path = tmp_path / "sample.schema.yaml"
    compile_model(SampleModel, schema_path, contract_id="example:Sample/v1")
    doc = tmp_path / "sample.md"
    write_doc(
        doc,
        """
        sample:
          name: hello
          direction: up
          delta: 1.5
        """,
    )
    contract = Contract(
        id="example:Sample/v1",
        envelope_key="sample",
        schema_path=Path("sample.schema.yaml"),
    )

    result = validate_artifact(doc, contract=contract)

    assert result.ok


def test_validate_artifact_reports_missing_schema_sidecar(tmp_path: Path) -> None:
    doc = tmp_path / "sample.md"
    write_doc(
        doc,
        """
        sample:
          name: hello
          direction: up
          delta: 1.5
        """,
    )
    contract = Contract(
        id="example:Sample/v1",
        envelope_key="sample",
        schema_path=Path("missing.schema.yaml"),
    )

    result = validate_artifact(doc, contract=contract)

    assert not result.ok
    assert result.structural.errors[0]["kind"] == "schema_sidecar_missing"
    assert result.semantic.skipped_reason == "no_pydantic_model"


def test_registry_registers_complete_bindings_only() -> None:
    registry = Contracts()
    contract = Contract(id="example:Sample/v1", model=SampleModel)
    registry.register(contract)

    assert registry.resolve("example:Sample/v1") == contract
    with pytest.raises(ValueError, match="already registered"):
        registry.register(Contract(id="example:Sample/v1", model=EnvelopeModel))


def write_doc(path: Path, frontmatter_yaml: str, body: str = "# title\n\nbody.\n") -> None:
    path.write_text(f"---\n{frontmatter_yaml}\n---\n{body}")
