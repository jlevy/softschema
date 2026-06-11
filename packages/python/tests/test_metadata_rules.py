"""Spec metadata rules: unknown ``softschema:`` keys and malformed contract IDs."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from softschema import Contract, parse_schema_metadata, validate_artifact


def test_unknown_softschema_key_is_rejected() -> None:
    with pytest.raises(ValidationError, match="bogus"):
        parse_schema_metadata({"contract": "t:X/v1", "bogus": 1})


def test_empty_contract_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_schema_metadata({"contract": ""})


def test_compact_string_form_still_parses() -> None:
    metadata = parse_schema_metadata("t:X/v1")
    assert metadata is not None
    assert metadata.contract_id == "t:X/v1"


def test_validate_artifact_reports_unknown_key_as_document_softschema_invalid(
    tmp_path: Path,
) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text(
        "---\nsoftschema:\n  contract: t:X/v1\n  bogus: 1\npayload:\n  a: 1\n---\nbody\n",
        encoding="utf-8",
    )
    contract = Contract(id="t:X/v1", envelope_key="payload")

    result = validate_artifact(doc, contract=contract)

    assert result.structural.ok is False
    assert result.structural.errors[0]["kind"] == "document_softschema_invalid"
