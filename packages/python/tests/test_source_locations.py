from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any, cast

import pytest

from softschema.core import NodeSource, SourceMap, SourcePoint, SourceSpan
from softschema.validate import (
    read_frontmatter,
    read_frontmatter_with_locations,
    read_yaml_artifact_with_locations,
)
from softschema.value_domain import (
    PortableValueError,
    PortableYamlSyntaxError,
    parse_portable_yaml,
    parse_portable_yaml_with_locations,
)

ROOT = Path(__file__).parents[3]
VECTORS: dict[str, Any] = json.loads(
    (ROOT / "tests/diagnostics/source-location-vectors.json").read_text(encoding="utf-8")
)
SOURCE_SEPARATOR_VECTORS: dict[str, Any] = json.loads(
    (ROOT / "tests/value-domain/source-separator-vectors.json").read_text(encoding="utf-8")
)


def _point(point: SourcePoint) -> dict[str, int]:
    return {"line": point.line, "column": point.column}


def _span(span: SourceSpan) -> dict[str, dict[str, int]]:
    return {"start": _point(span.start), "end": _point(span.end)}


def _node(node: NodeSource) -> dict[str, Any]:
    return {
        **({"key": _span(node.key)} if node.key is not None else {}),
        "value": _span(node.value),
    }


def _nodes(source_map: SourceMap) -> dict[str, Any]:
    return {pointer: _node(node) for pointer, node in source_map.nodes.items()}


@pytest.mark.parametrize("vector", VECTORS["cases"], ids=lambda item: item["id"])
def test_shared_source_location_vectors(tmp_path: Path, vector: dict[str, Any]) -> None:
    if "error" in vector:
        if vector["kind"] == "frontmatter":
            source = tmp_path / "artifact.md"
            source.write_bytes(vector["content"].encode())
            error_type = PortableYamlSyntaxError
            operation = lambda: read_frontmatter_with_locations(source)
        else:
            error_type = PortableValueError
            operation = lambda: parse_portable_yaml_with_locations(vector["content"])

        with pytest.raises(error_type) as caught:
            operation()
        expected = vector["error"]
        assert caught.value.line == expected["line"]
        assert caught.value.column == expected["column"]
        if "path" in expected:
            assert caught.value.path == expected["path"]
        return

    if vector["kind"] == "frontmatter":
        source = tmp_path / "artifact.md"
        source.write_bytes(vector["content"].encode())
        parsed = read_frontmatter_with_locations(source)
        value, source_map = parsed.value, parsed.source_map
    else:
        parsed_yaml = parse_portable_yaml_with_locations(vector["content"])
        value, source_map = parsed_yaml.value, parsed_yaml.source_map

    assert value == vector["value"]
    assert _nodes(source_map) == vector["nodes"]

    projection = vector.get("projection")
    if projection is not None:
        projected = source_map.project(projection["prefix"])
        assert (
            _node(projected.node("") or pytest.fail("projected root missing")) == projection["root"]
        )
        for lookup in projection["lookups"]:
            span = projected.span(lookup["pointer"], anchor=lookup["anchor"])
            assert span is not None
            assert _span(span) == lookup["span"]
        assert projected.span("/not-present", nearest=False) is None


@pytest.mark.parametrize(
    "vector",
    SOURCE_SEPARATOR_VECTORS["literal_cases"],
    ids=lambda item: item["id"],
)
def test_literal_nonportable_source_separators_have_shared_locations(
    vector: dict[str, Any],
) -> None:
    with pytest.raises(PortableValueError) as caught:
        parse_portable_yaml_with_locations(vector["yaml"])

    assert str(caught.value) == SOURCE_SEPARATOR_VECTORS["value_error_message"]
    assert caught.value.path == ""
    assert (caught.value.line, caught.value.column) == (
        vector["line"],
        vector["column"],
    )


def test_escaped_nonportable_source_separators_remain_string_values() -> None:
    vector = SOURCE_SEPARATOR_VECTORS["escaped_case"]

    assert parse_portable_yaml_with_locations(vector["yaml"]).value == vector["value"]


def test_nonportable_separator_cannot_create_a_markdown_frontmatter_fence(
    tmp_path: Path,
) -> None:
    for index, separator in enumerate(("\u0085", "\u2028", "\u2029")):
        source = tmp_path / f"artifact-{index}.md"
        text = f"---{separator}\nbody\n"
        source.write_text(text, encoding="utf-8")

        parsed = read_frontmatter_with_locations(source)

        assert parsed.content == text
        assert parsed.value is None
        assert parsed.source_map.nodes == {}


def test_source_map_is_immutable_and_copies_input() -> None:
    span = SourceSpan(SourcePoint(1, 1), SourcePoint(1, 2))
    entries = {"": NodeSource(value=span)}
    source_map = SourceMap(entries)
    entries.clear()

    assert source_map.node("") == NodeSource(value=span)
    with pytest.raises(TypeError):
        cast(Any, source_map.nodes)[""] = NodeSource(value=span)
    node = source_map.node("")
    assert node is not None
    with pytest.raises(FrozenInstanceError):
        cast(Any, node.value.start).line = 2


def test_legacy_parsers_keep_their_return_shapes_without_a_second_parse(tmp_path: Path) -> None:
    yaml_text = "root:\n  child: value\n"
    assert parse_portable_yaml(yaml_text) == {"root": {"child": "value"}}

    source = tmp_path / "artifact.md"
    source.write_text(f"---\n{yaml_text}---\nbody\n", encoding="utf-8")
    content, value = read_frontmatter(source)
    assert content == "body\n"
    assert value == {"root": {"child": "value"}}


def test_pure_yaml_reader_exposes_the_same_source_map(tmp_path: Path) -> None:
    vector = next(item for item in VECTORS["cases"] if item["id"] == "yaml-bom-crlf-unicode-key")
    source = tmp_path / "artifact.yaml"
    source.write_bytes(vector["content"].encode())

    parsed = read_yaml_artifact_with_locations(source)

    assert parsed.value == vector["value"]
    assert _nodes(parsed.source_map) == vector["nodes"]
