from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from ruamel.yaml import YAML

from softschema import compile_model, validate_structural
from softschema._identity import identity_problem
from softschema._portable import parse_yaml

IDENTITY_VECTORS = Path(__file__).resolve().parents[3] / "tests/vectors/identities.yaml"
ROOT = "https://example.com/root.json"


class Named(BaseModel):
    name: str


def _vectors() -> dict[str, list[dict[str, Any]]]:
    return YAML(typ="safe").load(IDENTITY_VECTORS.read_text())


def _schema_with(identity: str, *, nested: bool) -> dict[str, Any]:
    if nested:
        return {"$id": ROOT, "type": "object", "$defs": {"X": {"$id": identity, "type": "string"}}}
    return {"$id": identity, "type": "object"}


def _structural(tmp_path: Path, schema: dict[str, Any]) -> Any:
    path = tmp_path / "identity.schema.json"
    path.write_text(json.dumps(schema))
    return validate_structural({"name": "n"}, path)


def test_identity_grammar_refusals(tmp_path: Path) -> None:
    # The grammar names the same rule as TypeScript's; compile refuses a root identity as
    # the schema id, and validation refuses it as the `$id`, with one message.
    out = tmp_path / "named.schema.yaml"
    for case in _vectors()["refuse"]:
        identity, nested = case["id"], case.get("nested", False)
        assert identity_problem(identity, absolute=not nested) == case["problem"], identity
        label = "a $id" if nested else "the root $id"
        message = f"{label} must {case['problem']}, got {json.dumps(identity, ensure_ascii=False)}"
        structural = _structural(tmp_path, _schema_with(identity, nested=nested))
        assert structural.execution == "not_run", identity
        assert structural.errors[0]["reason"] == "resource_identity", identity
        assert structural.errors[0]["message"] == message, identity
        if not nested:
            # A ValueError, so the CLI reports it with exit 2.
            with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
                compile_model(Named, out, contract_id="example:Named/v1", schema_id=identity)
    assert not out.exists()


def test_identity_grammar_acceptances(tmp_path: Path) -> None:
    out = tmp_path / "named.schema.yaml"
    for case in _vectors()["accept"]:
        identity, nested = case["id"], case.get("nested", False)
        assert identity_problem(identity, absolute=not nested) is None, identity
        structural = _structural(tmp_path, _schema_with(identity, nested=nested))
        assert structural.execution == "completed", identity
        if not nested:
            compile_model(Named, out, contract_id="example:Named/v1", schema_id=identity)
            assert parse_yaml(out.read_text())["$id"] == identity
            assert validate_structural({"name": "n"}, out).ok, identity
