from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from ruamel.yaml import YAML

from softschema import (
    Contract,
    Contracts,
    SchemaProfile,
    SchemaStatus,
    compile_model,
    parse_schema_metadata,
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


HARDENING_VECTORS = Path(__file__).resolve().parents[3] / "tests/vectors/hardening.yaml"


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


def test_validate_artifact_without_envelope_key_infers_single_envelope(tmp_path: Path) -> None:
    """Per the spec, a contract with no envelope_key uses single-key inference."""
    schema_path = tmp_path / "sample.schema.yaml"
    compile_model(SampleModel, schema_path, contract_id="example:Sample/v1")
    doc = tmp_path / "doc.md"
    write_doc(doc, "sample:\n  name: hello\n  direction: up\n  delta: 1.5\n")
    contract = Contract(
        id="example:Sample/v1",
        model=SampleModel,
        schema_path=schema_path,
    )

    result = validate_artifact(doc, contract=contract)

    assert result.ok
    assert result.values == {"name": "hello", "direction": "up", "delta": 1.5}


def test_validate_artifact_without_envelope_key_rejects_multi_key_root(tmp_path: Path) -> None:
    """Multi-key documents are ambiguous; the spec requires explicit designation."""
    doc = tmp_path / "doc.md"
    write_doc(doc, "name: hello\ndirection: up\ndelta: 1.5\n")
    contract = Contract(id="example:Sample/v1", model=SampleModel)

    result = validate_artifact(doc, contract=contract)

    assert result.structural.ok is False
    error = result.structural.errors[0]
    assert error["kind"] == "envelope_ambiguous"
    assert "name" in error["message"]


def test_validate_artifact_without_envelope_key_rejects_zero_key_root(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    write_doc(doc, "softschema:\n  contract: example:Sample/v1\n")
    contract = Contract(id="example:Sample/v1", model=SampleModel)

    result = validate_artifact(doc, contract=contract)

    assert result.structural.ok is False
    assert result.structural.errors[0]["kind"] == "envelope_missing"


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


def test_validate_artifact_reports_yaml_parse_error_for_malformed_pure_yaml(tmp_path: Path) -> None:
    doc = tmp_path / "bad.yaml"
    doc.write_text("key: [unclosed\n  : : :\n")
    contract = Contract(id="example:Sample/v1", profile=SchemaProfile.pure_yaml)

    result = validate_artifact(doc, contract=contract)

    assert not result.ok
    assert result.structural.errors[0]["kind"] == "yaml_parse_error"


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


def test_validate_artifact_reports_missing_schema(tmp_path: Path) -> None:
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
    assert result.structural.errors[0]["kind"] == "schema_missing"
    assert result.semantic.skipped_reason == "no_semantic_model"


def test_registry_registers_complete_bindings_only() -> None:
    registry = Contracts()
    contract = Contract(id="example:Sample/v1", model=SampleModel)
    registry.register(contract)

    assert registry.resolve("example:Sample/v1") == contract
    with pytest.raises(ValueError, match="already registered"):
        registry.register(Contract(id="example:Sample/v1", model=EnvelopeModel))


def test_validate_artifact_returns_input_error_for_missing_file_frontmatter() -> None:
    contract = Contract(id="example:Sample/v1", model=SampleModel)
    result = validate_artifact(Path("/nonexistent.md"), contract=contract)

    assert not result.ok
    assert result.structural.ok is False
    assert result.structural.errors[0]["kind"] == "artifact_unreadable"
    assert result.outcome == "input_error"


def test_validate_artifact_returns_input_error_for_missing_file_pure_yaml() -> None:
    contract = Contract(
        id="example:Sample/v1",
        model=SampleModel,
        profile=SchemaProfile.pure_yaml,
    )
    result = validate_artifact(Path("/nonexistent.yaml"), contract=contract)

    assert not result.ok
    assert result.structural.ok is False
    assert result.structural.errors[0]["kind"] == "artifact_unreadable"
    assert result.outcome == "input_error"


def test_shared_portable_yaml_vectors(tmp_path: Path) -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    contract = Contract(id="example:Portable/v1", profile=SchemaProfile.pure_yaml)
    for case in vectors["portable_values"]:
        path = tmp_path / f"{case['id']}.yaml"
        text = "value: " + "[" * 65 + "0" + "]" * 65 if case.get("generated") else case["text"]
        path.write_text(text)
        result = validate_artifact(path, contract=contract)
        assert result.ok is case["valid"], case["id"]
        if not case["valid"]:
            assert result.structural.errors[0]["kind"] == case["code"], case["id"]


def test_shared_artifact_input_vectors(tmp_path: Path) -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    contract = Contract(id="example:Portable/v1", profile=SchemaProfile.pure_yaml)
    for case in vectors["artifact_input"]:
        path = tmp_path / f"{case['id']}.yaml"
        if case.get("source") == "invalid_utf8":
            path.write_bytes(b"value: \xff")
        elif case.get("source") == "too_large":
            path.write_bytes(b"x" * 1_048_577)
        elif "text" in case:
            path.write_text(case["text"])
        result = validate_artifact(path, contract=contract)
        assert result.outcome == case["outcome"], case["id"]
        assert result.structural.errors[0]["kind"] == case["code"], case["id"]


def write_doc(path: Path, frontmatter_yaml: str, body: str = "# title\n\nbody.\n") -> None:
    path.write_text(f"---\n{frontmatter_yaml}\n---\n{body}")


def test_pure_yaml_softschema_block_is_metadata_not_payload(tmp_path: Path) -> None:
    """Pure-yaml follows the same metadata rules: the block is recognized and
    stripped, never validated as payload data."""
    doc = tmp_path / "doc.yaml"
    doc.write_text(
        "softschema:\n  contract: example:Sample/v1\nname: hello\ndirection: up\ndelta: 1.5\n"
    )
    contract = Contract(id="example:Sample/v1", model=SampleModel, profile=SchemaProfile.pure_yaml)

    result = validate_artifact(doc, contract=contract)

    assert result.ok
    assert result.values == {"name": "hello", "direction": "up", "delta": 1.5}
    assert result.document_metadata is not None
    assert result.document_metadata.contract_id == "example:Sample/v1"


def test_pure_yaml_contract_mismatch_is_detected(tmp_path: Path) -> None:
    doc = tmp_path / "doc.yaml"
    doc.write_text("softschema:\n  contract: example:Sample/v1\nname: hello\n")
    contract = Contract(id="other:Thing/v1", profile=SchemaProfile.pure_yaml)

    result = validate_artifact(doc, contract=contract)

    assert result.structural.errors[0]["kind"] == "document_contract_mismatch"


def test_pure_yaml_explicit_envelope_key_nests_the_payload(tmp_path: Path) -> None:
    doc = tmp_path / "doc.yaml"
    doc.write_text(
        "softschema:\n  contract: example:Sample/v1\n"
        "sample:\n  name: hello\n  direction: up\n  delta: 1.5\n"
    )
    contract = Contract(
        id="example:Sample/v1",
        model=SampleModel,
        profile=SchemaProfile.pure_yaml,
        envelope_key="sample",
    )

    result = validate_artifact(doc, contract=contract)

    assert result.ok
    assert result.values == {"name": "hello", "direction": "up", "delta": 1.5}


def test_validate_artifact_uses_preread_frontmatter_without_reopening(tmp_path: Path) -> None:
    """When frontmatter is supplied, validate_artifact does not re-read the file
    (the CLI passes its single parse). Proven by pointing at a nonexistent path."""
    contract = Contract(id="example:Sample/v1", model=SampleModel, envelope_key="sample")
    preread = {
        "softschema": {"contract": "example:Sample/v1"},
        "sample": {"name": "hello", "direction": "up", "delta": 1.5},
    }

    result = validate_artifact(
        tmp_path / "does-not-exist.md", contract=contract, frontmatter=preread
    )

    assert result.ok
    assert result.values == {"name": "hello", "direction": "up", "delta": 1.5}


@pytest.mark.parametrize(
    "contract_id",
    [
        "Name",  # bare name
        "ns:Name",  # namespaced
        "ns:Name/v1",  # versioned
        "ns_x:Na_me",  # underscores
        "a.b.c:Name",  # dotted namespace
        "name",  # lowercase name (UpperCamelCase is advisory)
        "com.acme.docs:IncidentReview/1.0",  # dotted version
    ],
)
def test_contract_grammar_accepts_valid_ids(contract_id: str) -> None:
    metadata = parse_schema_metadata(contract_id)
    assert metadata is not None
    assert metadata.contract_id == contract_id


@pytest.mark.parametrize(
    "contract_id",
    [
        " ",  # whitespace only
        "bad id",  # internal whitespace
        "a : B",  # whitespace around separators
        ":Name",  # empty namespace segment
        "a::B",  # repeated colon
        "Name/v1/v2",  # repeated slash
        "Name/",  # empty version
        "ns:",  # missing name
        "My.Name",  # dots only allowed in the namespace (before the colon)
    ],
)
def test_contract_grammar_rejects_malformed_ids(contract_id: str) -> None:
    with pytest.raises(ValidationError):
        parse_schema_metadata(contract_id)
