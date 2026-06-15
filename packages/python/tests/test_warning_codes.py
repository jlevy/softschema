"""Regression tests pinning the public warning-code surface.

Downstream consumers filter on warning codes. Any addition or rename must update
both the ``WarningCode`` enum and the Warning Codes table in
``docs/softschema-python-design.md``; these tests fail when the two drift.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from softschema import (
    Contract,
    Contracts,
    SchemaStatus,
    WarningCode,
    validate_artifact,
)

DOCS_PATH = Path(__file__).resolve().parents[3] / "docs/softschema-python-design.md"


class _MoviePage(BaseModel):
    title: str


def _make_artifact(tmp_path: Path, frontmatter: str) -> Path:
    path = tmp_path / "doc.md"
    path.write_text(f"---\n{frontmatter}\n---\n# body\n", encoding="utf-8")
    return path


def _make_registry(contract: str, status: SchemaStatus) -> Contracts:
    registry = Contracts()
    registry.register(
        Contract(
            id=contract,
            model=_MoviePage,
            envelope_key="movie",
            status=status,
        )
    )
    return registry


def test_all_warning_codes_use_document_prefix() -> None:
    for code in WarningCode:
        assert code.value.startswith("document-"), (
            f"WarningCode.{code.name} value {code.value!r} must start with 'document-'"
        )


def test_warning_codes_documented_in_python_design() -> None:
    text = DOCS_PATH.read_text(encoding="utf-8")
    for code in WarningCode:
        assert f"`{code.value}`" in text, (
            f"WarningCode.{code.name} ({code.value!r}) is missing from the Warning Codes "
            f"table in {DOCS_PATH.name}"
        )


def test_document_contract_mismatch_emitted_in_advisory_mode(tmp_path: Path) -> None:
    artifact = _make_artifact(
        tmp_path,
        "softschema:\n  contract: example.movies:OtherContract/v1\nmovie:\n  title: x",
    )
    registry = _make_registry("example.movies:MoviePage/v1", SchemaStatus.soft)
    result = validate_artifact(
        artifact,
        contract_id="example.movies:MoviePage/v1",
        registry=registry,
        metadata_mode="advisory",
    )
    codes = [w.code for w in result.warnings]
    assert WarningCode.DOCUMENT_CONTRACT_MISMATCH.value in codes


def test_document_status_mismatch_emitted(tmp_path: Path) -> None:
    artifact = _make_artifact(
        tmp_path,
        "softschema:\n  contract: example.movies:MoviePage/v1\n  status: enforced\n"
        "movie:\n  title: x",
    )
    registry = _make_registry("example.movies:MoviePage/v1", SchemaStatus.permissive)
    result = validate_artifact(
        artifact,
        contract_id="example.movies:MoviePage/v1",
        registry=registry,
    )
    codes = [w.code for w in result.warnings]
    assert WarningCode.DOCUMENT_STATUS_MISMATCH.value in codes


def test_no_undocumented_codes_emitted_in_smoke_run(tmp_path: Path) -> None:
    """Run every warning-emitting code path; assert every code is in the enum."""
    known = {code.value for code in WarningCode}

    contract_mismatch_artifact = _make_artifact(
        tmp_path,
        "softschema:\n  contract: example.movies:OtherContract/v1\nmovie:\n  title: x",
    )
    registry = _make_registry("example.movies:MoviePage/v1", SchemaStatus.soft)
    advisory_result = validate_artifact(
        contract_mismatch_artifact,
        contract_id="example.movies:MoviePage/v1",
        registry=registry,
        metadata_mode="advisory",
    )

    status_mismatch_artifact = _make_artifact(
        tmp_path,
        "softschema:\n  contract: example.movies:MoviePage/v1\n  status: enforced\n"
        "movie:\n  title: x",
    )
    enforced_result = validate_artifact(
        status_mismatch_artifact,
        contract_id="example.movies:MoviePage/v1",
        registry=_make_registry("example.movies:MoviePage/v1", SchemaStatus.permissive),
    )

    emitted = {w.code for w in advisory_result.warnings} | {
        w.code for w in enforced_result.warnings
    }
    unexpected = emitted - known
    assert not unexpected, (
        f"Validation emitted codes {sorted(unexpected)} not in WarningCode. "
        "Add the new code to WarningCode and the Warning Codes table, or rename it."
    )
