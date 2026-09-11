"""A verdict must say which mechanism decided it, not only whether it passed.

`status` states intended maturity and binds nothing. So a document declaring `enforced`
and validated with nothing bound comes back `valid` with an empty error list, because
there was nothing to disagree with. That verdict is honest about the check it ran and
silent about the check it did not, and the two are indistinguishable to anything reading
`outcome`.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from softschema.compile import compile_model
from softschema.models import Contract, SchemaStatus, WarningCode
from softschema.pipeline import repair_and_validate_artifact
from softschema.validate import validate_artifact


class Sample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


def write_doc(path: Path, payload: str, status: str = "enforced") -> None:
    path.write_text(
        "---\n"
        "softschema:\n"
        "  contract: example:Sample/v1\n"
        "  envelope: sample\n"
        f"  status: {status}\n"
        f"{payload}"
        "---\n"
        "# body\n"
    )


def test_enforced_with_nothing_bound_is_reported_not_silently_passed(tmp_path: Path) -> None:
    """The failure this exists to prevent: a claim of strictness that checked nothing."""
    doc = tmp_path / "doc.md"
    write_doc(doc, "sample:\n  name: hello\n")
    contract = Contract(id="example:Sample/v1", status=SchemaStatus.enforced)

    result = validate_artifact(doc, contract=contract)

    assert result.enforcement_applied == "none"
    codes = [warning.code for warning in result.warnings]
    assert WarningCode.DOCUMENT_ENFORCEMENT_NOT_APPLIED.value in codes


def test_enforced_via_model_only_says_so(tmp_path: Path) -> None:
    """A model closes the object in its own language and says nothing to any other.

    That is a real check and a weaker promise than the word `enforced` names, so it is
    reported as its own level rather than folded into either neighbour.
    """
    doc = tmp_path / "doc.md"
    write_doc(doc, "sample:\n  name: hello\n")
    contract = Contract(id="example:Sample/v1", model=Sample, status=SchemaStatus.enforced)

    result = validate_artifact(doc, contract=contract)

    assert result.enforcement_applied == "model"
    codes = [warning.code for warning in result.warnings]
    assert WarningCode.DOCUMENT_ENFORCEMENT_VIA_MODEL_ONLY.value in codes


def test_enforced_with_a_bound_schema_is_silent(tmp_path: Path) -> None:
    """The healthy case warns about nothing, or the warning means nothing."""
    schema_path = tmp_path / "sample.schema.yaml"
    compile_model(Sample, schema_path, contract_id="example:Sample/v1")
    doc = tmp_path / "doc.md"
    write_doc(doc, "sample:\n  name: hello\n")
    contract = Contract(
        id="example:Sample/v1",
        model=Sample,
        schema_path=schema_path,
        status=SchemaStatus.enforced,
    )

    result = validate_artifact(doc, contract=contract)

    assert result.ok
    assert result.enforcement_applied == "schema"
    assert [warning.code for warning in result.warnings] == []


def test_a_bound_schema_that_cannot_be_read_applied_nothing(tmp_path: Path) -> None:
    """A named schema is not an applied one.

    Deriving the mechanism from `structural.skipped_reason` reports `schema` here,
    because a failure to load the schema skips nothing and validates nothing. That is
    the same false assurance in a new field, so the mechanism is recorded where the
    check would have run.
    """
    doc = tmp_path / "doc.md"
    write_doc(doc, "sample:\n  name: hello\n")
    contract = Contract(
        id="example:Sample/v1",
        schema_path=tmp_path / "absent.schema.yaml",
        status=SchemaStatus.enforced,
    )

    result = validate_artifact(doc, contract=contract)

    assert result.outcome == "invalid"
    assert result.enforcement_applied == "none"
    codes = [warning.code for warning in result.warnings]
    assert WarningCode.DOCUMENT_ENFORCEMENT_NOT_APPLIED.value in codes


def test_a_soft_document_is_not_warned_about(tmp_path: Path) -> None:
    """Only a shortfall against a claim is a finding. `soft` claims nothing."""
    doc = tmp_path / "doc.md"
    write_doc(doc, "sample:\n  name: hello\n", status="soft")
    contract = Contract(id="example:Sample/v1", status=SchemaStatus.soft)

    result = validate_artifact(doc, contract=contract)

    assert result.enforcement_applied == "none"
    assert [warning.code for warning in result.warnings] == []


def test_enforcement_applied_is_reported_for_every_verdict(tmp_path: Path) -> None:
    """A reader needs it beside `outcome` on every result, not only on a shortfall."""
    doc = tmp_path / "doc.md"
    write_doc(doc, "sample:\n  name: hello\n", status="permissive")
    contract = Contract(id="example:Sample/v1", model=Sample, status=SchemaStatus.permissive)

    result = validate_artifact(doc, contract=contract)

    assert result.enforcement_applied == "model"
    assert [warning.code for warning in result.warnings] == []


def test_a_repaired_result_keeps_the_mechanism_it_was_judged_by(tmp_path: Path) -> None:
    """The repair pass copies the result; a field it drops is a field consumers lose."""
    schema_path = tmp_path / "sample.schema.yaml"
    compile_model(Sample, schema_path, contract_id="example:Sample/v1")
    doc = tmp_path / "doc.md"
    write_doc(doc, "sample:\n  name: hello\n")
    contract = Contract(
        id="example:Sample/v1",
        schema_path=schema_path,
        status=SchemaStatus.enforced,
    )

    result = repair_and_validate_artifact(doc, contract=contract, write=False)

    assert result.enforcement_applied == "schema"
