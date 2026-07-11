from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from softschema.canonicalize import canonicalize_json_schema
from softschema.compile import _canonical_json

HARDENING_VECTORS = Path(__file__).resolve().parents[3] / "tests/vectors/hardening.yaml"


def test_preserves_title_annotations_and_title_named_property() -> None:
    schema = {
        "type": "object",
        "title": "Movie",
        "properties": {
            "title": {"type": "string", "title": "Title"},
            "year": {"type": "integer", "title": "Year"},
        },
    }

    out = canonicalize_json_schema(schema)

    assert out["title"] == "Movie"
    assert set(out["properties"]) == {"title", "year"}
    assert out["properties"]["title"]["title"] == "Title"
    assert out["properties"]["title"]["type"] == "string"


def test_preserves_default_annotations() -> None:
    schema = {
        "type": "object",
        "properties": {
            "a": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
            "b": {"type": "integer", "default": 0},
            "default": {"type": "string"},  # a property literally named "default"
        },
    }

    out = canonicalize_json_schema(schema)

    assert out["properties"]["a"]["default"] is None
    assert out["properties"]["b"]["default"] == 0
    assert "default" in out["properties"]  # the property named "default" survives


def test_rewrites_oneof_nullable_union_to_anyof() -> None:
    schema = {
        "type": "object",
        "properties": {
            "x": {"oneOf": [{"type": "string"}, {"type": "null"}]},
            "y": {"oneOf": [{"type": "string"}, {"type": "integer"}]},  # not nullable
        },
    }

    out = canonicalize_json_schema(schema)

    assert out["properties"]["x"] == {"anyOf": [{"type": "string"}, {"type": "null"}]}
    assert "oneOf" in out["properties"]["y"]  # genuine unions are left alone


def test_shared_canonicalization_and_digest_vectors() -> None:
    vectors = YAML(typ="safe").load(HARDENING_VECTORS.read_text())
    for case in vectors["canonicalization"]:
        before = case["before"]
        after = canonicalize_json_schema(before)
        assert after == case["after"], case["id"]
        for value in ({}, {"items": []}, {"credit_card": "set"}):
            before_ok = not list(Draft202012Validator(before).iter_errors(value))
            after_ok = not list(Draft202012Validator(after).iter_errors(value))
            assert before_ok is after_ok, case["id"]
    for case in vectors["digests"]:
        assert _canonical_json(case["value"]) == case["canonical"], case["id"]
