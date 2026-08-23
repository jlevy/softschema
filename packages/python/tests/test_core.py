from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from ruamel.yaml import YAML

import softschema
from softschema import (
    Contract,
    Contracts,
    SchemaProfile,
    SchemaStatus,
    clear_validator_cache,
    compile_model,
    parse_schema_metadata,
    read_frontmatter_doc,
    read_yaml_doc,
    validate_artifact,
    validate_semantic,
    validate_structural,
    validate_values,
)
from softschema import validate as validate_module
from softschema._portable import PortableInputError, parse_yaml


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


class GeneratedTitleModel(BaseModel):
    camelCase: str


HARDENING_VECTORS = Path(__file__).resolve().parents[3] / "tests/vectors/hardening.yaml"


def test_package_root_exports_only_the_supported_surface() -> None:
    assert set(softschema.__all__) == {
        "ArtifactValidationResult",
        "CompileResult",
        "Contract",
        "Contracts",
        "EnvelopeAmbiguityError",
        "FieldInfo",
        "GeneratedSection",
        "RegenerateResult",
        "RepairKind",
        "SchemaMetadata",
        "SchemaProfile",
        "SchemaStatus",
        "SchemaView",
        "SchemaWarning",
        "SemanticResult",
        "SoftField",
        "SoftOwner",
        "SoftTier",
        "StructuralResult",
        "ValidationResult",
        "WarningCode",
        "clear_validator_cache",
        "compile_model",
        "infer_envelope_key",
        "parse_schema_metadata",
        "read_frontmatter_doc",
        "read_yaml_doc",
        "regenerate",
        "validate_artifact",
        "validate_semantic",
        "validate_structural",
        "validate_values",
    }


def test_compile_writes_json_schema_with_contract_id(tmp_path: Path) -> None:
    out = tmp_path / "sample.schema.yaml"

    result = compile_model(SampleModel, out, contract_id="example:Sample/v1")

    assert out.is_file()
    assert "$schema:" in result.schema_yaml
    assert "$id:" not in result.schema_yaml
    assert "contract: example:Sample/v1" in result.schema_yaml
    assert "schema_sha256" in result.schema_yaml
    assert result.schema_sha256 is not None


def test_compile_separates_optional_schema_id_and_reserves_metadata(tmp_path: Path) -> None:
    out = tmp_path / "sample.schema.yaml"
    result = compile_model(
        SampleModel,
        out,
        contract_id="example:Sample/v1",
        schema_id="https://example.com/schemas/sample-v1",
    )
    assert "$id: https://example.com/schemas/sample-v1" in result.schema_yaml

    class ReservedModel(BaseModel):
        model_config = ConfigDict(json_schema_extra={"x-softschema": {"custom": True}})

        name: str

    with pytest.raises(ValueError, match="reserved root identity key"):
        compile_model(ReservedModel, out, contract_id="example:Reserved/v1")


def test_compile_drift_is_portable_and_boolean_safe(tmp_path: Path) -> None:
    out = tmp_path / "sample.schema.yaml"
    compile_model(SampleModel, out, contract_id="example:Sample/v1")
    out.write_text(
        out.read_text().replace("additionalProperties: false", "additionalProperties: 0")
    )
    assert compile_model(SampleModel, out, contract_id="example:Sample/v1", check_only=True).drift
    out.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="UTF-8"):
        compile_model(SampleModel, out, contract_id="example:Sample/v1", check_only=True)


def test_shared_generated_title_vectors(tmp_path: Path) -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    for case in vectors["compiler_titles"]:
        out = tmp_path / f"{case['id']}.schema.yaml"
        compile_model(GeneratedTitleModel, out, contract_id=case["contract"])
        schema = YAML(typ="safe").load(out.read_text())
        assert schema["title"] == case["expected_root"], case["id"]
        assert schema["properties"][case["field"]]["title"] == case["expected_field"], case["id"]


def test_shared_contract_identity_vectors() -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    for case in vectors["identity"]:
        if case["valid"]:
            assert Contract(id=case["contract"]).id == case["contract"]
        else:
            with pytest.raises(ValidationError):
                Contract(id=case["contract"])


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


def test_validate_values_enforced_requires_a_structural_schema() -> None:
    result = validate_values(
        {"name": "hello", "bogus": 1},
        model=SampleModel,
        status=SchemaStatus.enforced,
    )

    assert not result.ok
    assert result.structural.errors == [
        {
            "kind": "enforced_schema_required",
            "message": "status 'enforced' requires a structural schema",
        }
    ]


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
    schema_path = tmp_path / "sample.schema.yaml"
    compile_model(SampleModel, schema_path, contract_id="example:Sample/v1")
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
        schema_path=schema_path,
    )

    result = validate_artifact(doc, contract=contract)

    assert result.ok
    assert result.contract_id == "example:Sample/v1"
    assert result.values == {"name": "hello", "direction": "up", "delta": 1.5}


def test_validate_artifact_accepts_pure_yaml(tmp_path: Path) -> None:
    schema_path = tmp_path / "sample.schema.yaml"
    compile_model(SampleModel, schema_path, contract_id="example:Sample/v1")
    doc = tmp_path / "sample.yaml"
    doc.write_text("name: hello\ndirection: up\ndelta: 1.5\n")
    contract = Contract(
        id="example:Sample/v1",
        model=SampleModel,
        profile=SchemaProfile.pure_yaml,
        status=SchemaStatus.enforced,
        schema_path=schema_path,
    )

    result = validate_artifact(doc, contract=contract)

    assert result.ok
    assert result.profile == SchemaProfile.pure_yaml
    assert result.values == {"name": "hello", "direction": "up", "delta": 1.5}


def test_validate_artifact_enforced_model_only_requires_schema(tmp_path: Path) -> None:
    doc = tmp_path / "sample.yaml"
    doc.write_text("name: hello\ndirection: up\ndelta: 1.5\nbogus: 1\n")
    contract = Contract(
        id="example:Sample/v1",
        model=SampleModel,
        profile=SchemaProfile.pure_yaml,
        status=SchemaStatus.enforced,
    )

    result = validate_artifact(doc, contract=contract)

    assert not result.ok
    assert result.structural.errors[0]["kind"] == "enforced_schema_required"


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


def test_document_schema_binding_rejects_symlink_escape(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    outside = tmp_path / "outside.schema.yaml"
    compile_model(SampleModel, outside, contract_id="example:Sample/v1")
    (docs / "linked.schema.yaml").symlink_to(outside)
    doc = docs / "sample.md"
    write_doc(
        doc,
        """
        softschema:
          contract: example:Sample/v1
          schema: linked.schema.yaml
          envelope: sample
        sample:
          name: hello
          direction: up
          delta: 1.5
        """,
    )
    contract = Contract(id="example:Sample/v1", envelope_key="sample")

    result = validate_artifact(doc, contract=contract)

    assert not result.ok
    assert result.structural.errors[0]["kind"] == "schema_missing"
    assert "escapes" in result.structural.errors[0]["message"]


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
        depth = int(case.get("depth", 1_000))
        text = (
            "value: " + "[" * depth + "0" + "]" * depth if case.get("generated") else case["text"]
        )
        path.write_text(text)
        result = validate_artifact(path, contract=contract)
        assert result.ok is case["valid"], case["id"]
        if "expected" in case:
            assert result.values == case["expected"], case["id"]
        if "code" in case:
            assert result.structural.errors[0]["kind"] == case["code"], case["id"]


def test_portable_timestamp_constructor_does_not_change_ruamel_defaults() -> None:
    before = YAML(typ="safe").load("value: 2026-07-11")["value"]
    assert type(before) is date

    assert parse_yaml("value: 2026-07-11") == {"value": "2026-07-11"}

    after = YAML(typ="safe").load("value: 2026-07-11")["value"]
    assert type(after) is date
    assert after == before


def test_timestamp_strings_are_validated_by_pydantic_semantics() -> None:
    class TimestampModel(BaseModel):
        date_value: date
        datetime_value: datetime

    valid = validate_semantic(
        {
            "date_value": "2026-07-11",
            "datetime_value": "2026-05-16T13:10:10-07:00",
        },
        TimestampModel,
    )
    invalid = validate_semantic(
        {"date_value": "2001-13-99", "datetime_value": "not-a-datetime"},
        TimestampModel,
    )

    assert valid.ok
    assert not invalid.ok


def test_shared_frontmatter_vectors(tmp_path: Path) -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    contract = Contract(id="example:Movie/v1", envelope_key="movie")
    for case in vectors["frontmatter"]:
        path = tmp_path / f"{case['id']}.md"
        path.write_text(case["text"])
        result = validate_artifact(path, contract=contract)
        assert result.ok, case["id"]
        assert result.values == case["expected"], case["id"]


def test_shared_artifact_input_vectors(tmp_path: Path) -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    contract = Contract(id="example:Portable/v1", profile=SchemaProfile.pure_yaml)
    for case in vectors["artifact_input"]:
        path = tmp_path / f"{case['id']}.yaml"
        if case.get("source") == "invalid_utf8":
            path.write_bytes(b"value: \xff")
        elif "text" in case:
            path.write_text(case["text"])
        result = validate_artifact(path, contract=contract)
        assert result.outcome == case["outcome"], case["id"]
        assert result.structural.errors[0]["kind"] == case["code"], case["id"]


def test_shared_structural_vectors(tmp_path: Path) -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    yaml = YAML()
    for case in vectors["structural"]:
        path = tmp_path / f"{case['id']}.schema.yaml"
        yaml.dump(case["schema"], path)
        result = validate_structural(case["value"], path, resources=case.get("resources"))
        assert result.ok is case["valid"], case["id"]
        if not case["valid"]:
            assert result.errors[0]["kind"] == case["code"], case["id"]
            if "reason" in case:
                assert result.errors[0]["reason"] == case["reason"], case["id"]


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

    result = validate_artifact(tmp_path / "does-not-exist.md", contract=contract, document=preread)

    assert result.ok
    assert result.values == {"name": "hello", "direction": "up", "delta": 1.5}


def test_validate_artifact_uses_preread_pure_yaml_without_reopening(tmp_path: Path) -> None:
    """A pure-yaml artifact honours a pre-parsed document too.

    Both profiles take the same parameter: a caller holding the parsed root should never
    have to know which profile it is on to avoid a second parse. No `envelope_key`, so
    this also covers the rule that separates the profiles: the root minus the metadata
    block IS the payload.
    """
    contract = Contract(
        id="example:Sample/v1",
        model=SampleModel,
        profile=SchemaProfile.pure_yaml,
    )
    preread = {
        "softschema": {"contract": "example:Sample/v1"},
        "name": "hello",
        "direction": "up",
        "delta": 1.5,
    }

    result = validate_artifact(
        tmp_path / "does-not-exist.yaml", contract=contract, document=preread
    )

    assert result.ok
    assert result.values == {"name": "hello", "direction": "up", "delta": 1.5}


def test_document_readers_apply_portable_yaml_rules(tmp_path: Path) -> None:
    """The public readers are what make a pre-parsed `document` equivalent to a disk read.

    A caller who decodes with a host YAML library instead loses these rules silently, so
    the readers must keep enforcing them.
    """
    merge_key_doc = "defaults: &d\n  name: hello\nsample:\n  <<: *d\n"
    yaml_path = tmp_path / "merge.yaml"
    yaml_path.write_text(merge_key_doc)
    md_path = tmp_path / "merge.md"
    md_path.write_text(f"---\n{merge_key_doc}---\n\nbody\n")

    for reader, path in ((read_yaml_doc, yaml_path), (read_frontmatter_doc, md_path)):
        with pytest.raises(PortableInputError) as caught:
            reader(path)
        assert caught.value.code == "yaml_merge_key"


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


def _write_schema(path: Path, *, required_field: str) -> None:
    path.write_text(
        "$schema: https://json-schema.org/draft/2020-12/schema\n"
        "type: object\n"
        "properties:\n"
        f"  {required_field}:\n"
        "    type: string\n"
        "required:\n"
        f"  - {required_field}\n",
        encoding="utf-8",
    )


def test_repeated_validation_reuses_one_compiled_validator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Compiling a schema is pure, so it should happen once per schema file.

    Recompiling per call — parse, dialect check, enforced overlay, registry
    crawl — dominated large suites well ahead of the actual validation work.
    """
    clear_validator_cache()
    schema = tmp_path / "sample.schema.yaml"
    _write_schema(schema, required_field="name")

    parses: list[str] = []
    original = parse_yaml

    def counting_parse(text: str) -> Any:
        parses.append(text)
        return original(text)

    monkeypatch.setattr(validate_module, "parse_yaml", counting_parse)
    for _ in range(5):
        assert validate_structural({"name": "ok"}, schema).ok

    assert parses.count(schema.read_text()) == 1, "compiled schema should be parsed once"


def test_rewriting_a_schema_is_not_served_from_the_cache(tmp_path: Path) -> None:
    """A regenerated schema must take effect, never a stale compiled copy."""
    schema = tmp_path / "sample.schema.yaml"
    _write_schema(schema, required_field="name")
    assert validate_structural({"name": "ok"}, schema).ok
    assert not validate_structural({"other": "ok"}, schema).ok

    _write_schema(schema, required_field="other_name")

    assert validate_structural({"other_name": "ok"}, schema).ok
    assert not validate_structural({"name": "ok"}, schema).ok


def test_same_size_rewrite_with_preserved_mtime_is_not_served_from_the_cache(
    tmp_path: Path,
) -> None:
    """Content decides the entry, so no stat pair can alias two schemas.

    A key of (path, mtime, size) served a stale validator here: the rewrite is
    the same length, and restoring the original mtime is what ``cp -p``,
    ``rsync -t``, ``tar -x``, and a restored CI cache all do.
    """
    clear_validator_cache()
    schema = tmp_path / "sample.schema.yaml"
    _write_schema(schema, required_field="aaaa")
    before = schema.stat()
    assert validate_structural({"aaaa": "ok"}, schema).ok

    _write_schema(schema, required_field="cccc")  # identical length
    os.utime(schema, ns=(before.st_mtime_ns, before.st_mtime_ns))
    after = schema.stat()
    assert (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns)

    assert validate_structural({"cccc": "ok"}, schema).ok
    assert not validate_structural({"aaaa": "ok"}, schema).ok


def test_identical_schemas_at_two_paths_share_one_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keying on content means a copied schema costs nothing to compile twice."""
    clear_validator_cache()
    first = tmp_path / "first.schema.yaml"
    second = tmp_path / "second.schema.yaml"
    _write_schema(first, required_field="name")
    _write_schema(second, required_field="name")

    parses: list[str] = []
    original = parse_yaml

    def counting_parse(text: str) -> Any:
        parses.append(text)
        return original(text)

    monkeypatch.setattr(validate_module, "parse_yaml", counting_parse)
    assert validate_structural({"name": "ok"}, first).ok
    assert validate_structural({"name": "ok"}, second).ok

    assert parses.count(first.read_text()) == 1


def test_clear_validator_cache_forces_a_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The escape hatch exists for processes that regenerate schemas in place."""
    clear_validator_cache()
    schema = tmp_path / "sample.schema.yaml"
    _write_schema(schema, required_field="name")
    assert validate_structural({"name": "ok"}, schema).ok

    parses: list[str] = []
    original = parse_yaml

    def counting_parse(text: str) -> Any:
        parses.append(text)
        return original(text)

    monkeypatch.setattr(validate_module, "parse_yaml", counting_parse)
    assert validate_structural({"name": "ok"}, schema).ok
    assert parses == [], "a warm entry should not reparse"

    clear_validator_cache()
    assert validate_structural({"name": "ok"}, schema).ok
    assert parses.count(schema.read_text()) == 1


def test_strict_extras_is_part_of_the_cache_key(tmp_path: Path) -> None:
    """The enforced overlay changes the validator, so it cannot share an entry."""
    schema = tmp_path / "sample.schema.yaml"
    _write_schema(schema, required_field="name")
    payload = {"name": "ok", "unexpected": 1}

    assert validate_structural(payload, schema, strict_extras=False).ok
    assert not validate_structural(payload, schema, strict_extras=True).ok
    # Re-run both to prove neither direction poisoned the other's entry.
    assert validate_structural(payload, schema, strict_extras=False).ok
    assert not validate_structural(payload, schema, strict_extras=True).ok


def test_a_schema_whose_root_is_not_a_mapping_still_reports_syntax(tmp_path: Path) -> None:
    """The cached path must preserve the original structured failure."""
    schema = tmp_path / "bad.schema.yaml"
    schema.write_text("- not\n- a mapping\n", encoding="utf-8")

    result = validate_structural({"name": "ok"}, schema)

    assert not result.ok
    assert result.errors[0]["kind"] == "schema_invalid"
