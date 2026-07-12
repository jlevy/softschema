"""SchemaView tests exercised against the movie-page example schema."""

from __future__ import annotations

from pathlib import Path

import pytest

from softschema import FieldInfo, SchemaView
from softschema._portable import parse_yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
MOVIE_SCHEMA = REPO_ROOT / "examples/movie_page/movie-page.schema.yaml"
HARDENING_VECTORS = REPO_ROOT / "tests/vectors/hardening.yaml"


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


def test_shared_schema_view_contract() -> None:
    vectors = parse_yaml(HARDENING_VECTORS.read_text(encoding="utf-8"))["schema_view"]

    ref_case = vectors[0]
    source = ref_case["schema"]
    view = SchemaView(source)
    source["properties"]["name"]["description"] = "mutated"
    field = view.field("/properties/name")
    assert {"description": field.description, "type": field.json_type} == ref_case["expected"]

    union_case = vectors[1]
    union = SchemaView(union_case["schema"]).field("/properties/value")
    assert union.json_type is union_case["expected"]["type"]

    identities = SchemaView(
        {
            "$id": "https://example.com/schemas/person-v1",
            "x-softschema": {"contract": "example.people:Person/v1"},
        }
    )
    assert identities.contract_id == "example.people:Person/v1"
    assert identities.schema_id == "https://example.com/schemas/person-v1"
    raw = identities.raw
    raw["$id"] = "mutated"
    assert identities.schema_id == "https://example.com/schemas/person-v1"
