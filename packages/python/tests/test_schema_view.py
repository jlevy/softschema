"""SchemaView tests exercised against the movie-page example schema."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from softschema import DEFAULT_VALIDATION_LIMITS, FieldInfo, SchemaView, infer_envelope_key
from softschema.value_domain import PortableValueError, PortableYamlSyntaxError
from tests.yaml_fixtures import load_yaml_fixture

REPO_ROOT = Path(__file__).resolve().parents[3]
MOVIE_SCHEMA = REPO_ROOT / "examples/movie_page/movie-page.schema.yaml"
VECTORS = load_yaml_fixture(REPO_ROOT / "tests/schema-view/vectors.yaml")


def _field_output(field: FieldInfo) -> dict[str, Any]:
    return {
        "pointer": field.pointer,
        "name": field.name,
        "json_type": field.json_type,
        "enum": field.enum,
        "required": field.required,
        "description": field.description,
        "softmeta": field.softmeta,
    }


@pytest.fixture
def view() -> SchemaView:
    return SchemaView.load(MOVIE_SCHEMA)


def test_load_exposes_contract_and_hash(view: SchemaView) -> None:
    assert view.contract_id == "example.movies:MoviePage/v1"
    assert view.schema_sha256 is not None
    assert len(view.schema_sha256) == 64  # SHA-256 hex digest


def test_root_softmeta_is_language_neutral(view: SchemaView) -> None:
    meta = view.root_softmeta
    assert meta["contract"] == "example.movies:MoviePage/v1"
    assert "softschema_format_version" in meta
    # No language-specific provenance (e.g. generated_from) leaks into the compiled schema.
    assert "generated_from" not in meta


def test_iter_fields_includes_root_and_nested(view: SchemaView) -> None:
    pointers = {f.pointer for f in view.iter_fields()}
    # Root-level fields.
    assert "/properties/title" in pointers
    assert "/properties/release_year" in pointers
    assert "/properties/cast" in pointers
    # Nested through a $ref into $defs.
    assert "/properties/ratings/properties/rotten_tomatoes" in pointers
    assert "/properties/ratings/properties/rotten_tomatoes/properties/critics_percent" in pointers
    assert "/properties/ratings/properties/imdb/properties/score" in pointers


def test_field_lookup_returns_typed_info(view: SchemaView) -> None:
    title = view.field("/properties/title")
    assert isinstance(title, FieldInfo)
    assert title.name == "title"
    assert title.json_type == "string"
    assert title.required is True
    assert title.enum is None


def test_field_lookup_missing_pointer_raises(view: SchemaView) -> None:
    with pytest.raises(ValueError, match="no field at pointer"):
        view.field("/properties/does_not_exist")


def test_enum_extraction_handles_optional_literal(view: SchemaView) -> None:
    # mpaa_rating is Literal[G, PG, PG-13, R, NC-17, NR] | None
    values = view.enum_values("/properties/mpaa_rating")
    assert values == ["G", "PG", "PG-13", "R", "NC-17", "NR"]


def test_required_fields_match_schema(view: SchemaView) -> None:
    required = {f.name for f in view.iter_fields() if f.required and "/" not in f.pointer[12:]}
    # Top-level requires from the model: title, release_year, runtime_minutes,
    # directors, genres, synopsis, ratings.
    assert {
        "title",
        "release_year",
        "runtime_minutes",
        "directors",
        "genres",
        "synopsis",
        "ratings",
    } <= required


def test_softmeta_retrieval_picks_up_soft_field_annotation(view: SchemaView) -> None:
    meta = view.softmeta("/properties/genres")
    assert meta["group"] == "taxonomy"
    assert meta["tier"] == "constrained"
    assert meta["owner"] == "agent"


def test_fields_by_group_owner_tier_filter(view: SchemaView) -> None:
    in_taxonomy = view.fields_by_group("taxonomy")
    assert [f.name for f in in_taxonomy] == ["genres"]

    by_owner = view.fields_by_owner("agent")
    assert any(f.name == "genres" for f in by_owner)

    by_tier = view.fields_by_tier("constrained")
    assert [f.name for f in by_tier] == ["genres"]


def test_load_rejects_non_mapping_root(tmp_path: Path) -> None:
    bad = tmp_path / "bad.schema.yaml"
    bad.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        SchemaView.load(bad)


def test_iter_fields_terminates_on_cyclic_ref() -> None:
    # A self-referential $def (Node.child -> Node). iter_fields must terminate by
    # tracking the followed $ref on the recursion path. This is a shared parity case
    # with the TypeScript test in schemaView.test.ts.
    cyclic = {
        "type": "object",
        "properties": {"root": {"$ref": "#/$defs/Node"}},
        "$defs": {
            "Node": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "child": {"$ref": "#/$defs/Node"},
                },
            }
        },
    }
    view = SchemaView(cyclic)
    pointers = [f.pointer for f in view.iter_fields()]
    assert pointers == [
        "/properties/root",
        "/properties/root/properties/name",
        "/properties/root/properties/child",
    ]
    # The cyclic `child` is surfaced as an unresolved leaf (no further recursion).
    assert view.field("/properties/root/properties/child").json_type is None


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda case: case["id"])
def test_shared_schema_view_vectors(case: dict[str, Any]) -> None:
    view = SchemaView(case["schema"])

    assert [_field_output(field) for field in view.iter_fields()] == case["fields"]


def test_constructor_and_accessors_are_defensive_deep_snapshots() -> None:
    schema: dict[str, Any] = {
        "x-softschema": {"nested": {"labels": ["root"]}},
        "type": "object",
        "properties": {
            "field": {
                "type": "string",
                "description": "original",
                "x-softschema": {"nested": {"labels": ["field"]}},
            }
        },
    }
    view = SchemaView(schema)

    schema["x-softschema"]["nested"]["labels"].append("constructor mutation")
    schema["properties"]["field"]["description"] = "mutated"
    raw = view.raw
    raw["x-softschema"]["nested"]["labels"].append("raw mutation")
    raw["properties"]["field"]["description"] = "raw mutation"
    root_meta = view.root_softmeta
    root_meta["nested"]["labels"].append("root meta mutation")
    field = view.field("/properties/field")
    field.softmeta["nested"]["labels"].append("field mutation")

    assert view.raw["x-softschema"]["nested"]["labels"] == ["root"]
    assert view.field("/properties/field").description == "original"
    assert view.softmeta("/properties/field") == {"nested": {"labels": ["field"]}}


def test_load_uses_the_portable_mapping_key_and_resource_limit_boundary(tmp_path: Path) -> None:
    bom = tmp_path / "bom.schema.yaml"
    bom.write_bytes(b"\xef\xbb\xbftype: object\n")
    assert SchemaView.load(bom).raw == {"type": "object"}

    non_string_key = tmp_path / "non-string.schema.yaml"
    non_string_key.write_text("1: value\n", encoding="utf-8")
    with pytest.raises(PortableValueError, match="mapping keys must be strings"):
        SchemaView.load(non_string_key)

    invalid_syntax = tmp_path / "invalid-syntax.schema.yaml"
    invalid_syntax.write_text("properties: [\n", encoding="utf-8")
    with pytest.raises(PortableYamlSyntaxError):
        SchemaView.load(invalid_syntax)

    invalid_utf8 = tmp_path / "invalid-utf8.schema.yaml"
    invalid_utf8.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        SchemaView.load(invalid_utf8)

    oversized = tmp_path / "oversized.schema.yaml"
    oversized.write_text("type: object\n", encoding="utf-8")
    with pytest.raises(PortableValueError, match="maximum resource size exceeded"):
        SchemaView.load(
            oversized,
            limits=replace(DEFAULT_VALIDATION_LIMITS, max_resource_bytes=1),
        )


def test_envelope_inference_consumes_normalized_string_keys_without_coercion() -> None:
    assert infer_envelope_key({"softschema": {}, "01": {}}) == "01"
