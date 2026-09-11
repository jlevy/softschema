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
from softschema.models import SchemaStatus
from softschema.registry import Contract
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
    assert "enforcement_not_applied" in codes


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
    assert "enforcement_via_model_only" in codes


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
