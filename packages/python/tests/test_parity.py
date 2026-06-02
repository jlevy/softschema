"""The comprehensive cross-language parity fixture compiles to the committed sidecar.

This guards the Python side of the parity contract: the Pydantic KitchenSink model must
keep compiling to the canonical `examples/parity/parity.schema.yaml`, which is the shared
reference the TypeScript/Zod fixture must also reproduce byte-for-byte.
"""

from __future__ import annotations

from pathlib import Path

from examples.parity.model import KitchenSink
from softschema import compile_model

REPO_ROOT = Path(__file__).resolve().parents[3]
PARITY_SCHEMA = REPO_ROOT / "examples/parity/parity.schema.yaml"
CONTRACT_ID = "example.parity:KitchenSink/v1"


def test_kitchen_sink_matches_committed_canonical_sidecar() -> None:
    result = compile_model(KitchenSink, PARITY_SCHEMA, contract_id=CONTRACT_ID, check_only=True)
    assert not result.drift, result.drift_diff


def test_kitchen_sink_sidecar_is_language_neutral() -> None:
    text = PARITY_SCHEMA.read_text()
    # No language-specific provenance leaks into the shared reference.
    assert "generated_from" not in text
    # required is sorted (set semantics, field-order independent).
    assert "- active\n- channels\n- code\n" in text
