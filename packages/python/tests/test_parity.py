"""The comprehensive cross-language parity fixture compiles to the committed schema.

This guards the Python side of the parity contract: the Pydantic KitchenSink model must
keep compiling to the canonical `examples/parity/parity.schema.yaml`, which is the
shared reference the TypeScript/Zod fixture must also reproduce.
"""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from examples.parity.model import KitchenSink
from softschema import compile_model

REPO_ROOT = Path(__file__).resolve().parents[3]
PARITY_SCHEMA = REPO_ROOT / "examples/parity/parity.schema.yaml"
HARDENING_VECTORS = REPO_ROOT / "tests/vectors/hardening.yaml"
CONTRACT_ID = "example.parity:KitchenSink/v1"


def test_kitchen_sink_matches_committed_canonical_schema() -> None:
    result = compile_model(KitchenSink, PARITY_SCHEMA, contract_id=CONTRACT_ID, check_only=True)
    assert not result.drift, result.drift_diff


def test_kitchen_sink_schema_is_language_neutral() -> None:
    text = PARITY_SCHEMA.read_text()
    assert "generated_from" not in text
    assert "- active\n- channels\n- code\n" in text


def test_shared_hardening_vectors_are_readable() -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    assert list(vectors) == [
        "artifact_input",
        "frontmatter",
        "portable_values",
        "structural",
        "canonicalization",
        "enforcement",
        "identity",
        "compiler_annotations",
        "compiler_titles",
        "schema_view",
        "digests",
    ]
    ids = [case["id"] for cases in vectors.values() for case in cases]
    assert len(ids) == len(set(ids))
