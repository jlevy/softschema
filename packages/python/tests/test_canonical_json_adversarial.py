"""Python-oracle checks for the shared canonical JSON parity vectors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from softschema.core import normalize_portable_value
from tests.yaml_fixtures import load_yaml_fixture

REPO_ROOT = Path(__file__).resolve().parents[3]
VECTORS = REPO_ROOT / "tests/parity/canonical-json-adversarial-vectors.yaml"


def test_adversarial_serialization_vectors_match_python_oracle() -> None:
    fixture: dict[str, Any] = load_yaml_fixture(VECTORS)
    assert fixture["format"] == "canonical-json-adversarial-v1"
    for vector in fixture["cases"]:
        normalized, _ = normalize_portable_value(vector["value"])
        compact = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        pretty = json.dumps(
            normalized,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        assert (vector["id"], compact, pretty) == (
            vector["id"],
            vector["compact"],
            vector["pretty"],
        )
        assert hashlib.sha256(compact.encode("utf-8")).hexdigest() == vector["sha256"]


def test_python_oracle_normalizes_signed_zero_and_integral_floats() -> None:
    fixture: dict[str, Any] = load_yaml_fixture(VECTORS)
    vector = next(
        item
        for item in fixture["cases"]
        if item["id"] == "normalized-float-and-exponent-boundaries"
    )
    normalized, _ = normalize_portable_value(vector["value"])
    assert isinstance(normalized, list)
    assert normalized[:4] == [0, 0, 1, -1]
    assert all(isinstance(value, int) for value in normalized[:4])
