from __future__ import annotations

from softschema.canonicalize import canonicalize_json_schema


def test_drops_title_keyword_but_keeps_title_named_property() -> None:
    schema = {
        "type": "object",
        "title": "Movie",
        "properties": {
            "title": {"type": "string", "title": "Title"},
            "year": {"type": "integer", "title": "Year"},
        },
    }

    out = canonicalize_json_schema(schema)

    assert "title" not in out  # the object-level title keyword is gone
    assert set(out["properties"]) == {"title", "year"}  # the named property survives
    assert "title" not in out["properties"]["title"]  # its own title keyword is gone
    assert out["properties"]["title"]["type"] == "string"


def test_strips_implicit_null_default_only() -> None:
    schema = {
        "type": "object",
        "properties": {
            "a": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
            "b": {"type": "integer", "default": 0},
            "default": {"type": "string"},  # a property literally named "default"
        },
    }

    out = canonicalize_json_schema(schema)

    assert "default" not in out["properties"]["a"]
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
