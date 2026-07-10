from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from softschema.cli import main as softschema_main
from softschema.core import SourceSpan
from softschema.value_domain import (
    DEFAULT_VALIDATION_LIMITS,
    PortableValueError,
    PortableYamlSyntaxError,
    parse_portable_yaml_with_locations,
)

ROOT = Path(__file__).parents[3]
VECTORS: dict[str, Any] = json.loads(
    (ROOT / "tests/value-domain/yaml-parity-edge-vectors.json").read_text(encoding="utf-8")
)


def _span(span: SourceSpan) -> dict[str, dict[str, int]]:
    return {
        "start": {"line": span.start.line, "column": span.start.column},
        "end": {"line": span.end.line, "column": span.end.column},
    }


def test_plain_compact_flow_colons_follow_the_shared_portable_policy() -> None:
    policy = VECTORS["compact_flow_policy"]
    for vector in policy["rejected"]:
        with pytest.raises(PortableYamlSyntaxError) as caught:
            parse_portable_yaml_with_locations(vector["yaml"])

        assert str(caught.value) == policy["message"]
        assert (caught.value.line, caught.value.column) == (
            vector["line"],
            vector["column"],
        )

    for vector in policy["accepted"]:
        assert parse_portable_yaml_with_locations(vector["yaml"]).value == vector["value"]

    with pytest.raises(PortableYamlSyntaxError):
        parse_portable_yaml_with_locations(
            "[a:]",
            limits=replace(DEFAULT_VALIDATION_LIMITS, max_nodes_per_resource=1),
        )


def test_yaml_parser_exceptions_with_codes_become_portable_syntax_errors() -> None:
    for vector in VECTORS["composer_syntax_errors"]:
        with pytest.raises(PortableYamlSyntaxError) as caught:
            parse_portable_yaml_with_locations(vector["yaml"])

        assert str(caught.value) == vector["message"]
        assert (caught.value.line, caught.value.column) == (
            vector["line"],
            vector["column"],
        )


def test_flow_opener_comments_require_separation_in_both_runtimes() -> None:
    policy = VECTORS["flow_opener_comment_policy"]
    for vector in policy["rejected"]:
        with pytest.raises(PortableYamlSyntaxError) as caught:
            parse_portable_yaml_with_locations(vector["yaml"])

        assert str(caught.value) == policy["message"]
        assert (caught.value.line, caught.value.column) == (
            vector["line"],
            vector["column"],
        )

    for vector in policy["accepted"]:
        assert parse_portable_yaml_with_locations(vector["yaml"]).value == vector["value"]


def test_tag_directives_expand_before_portable_tag_classification() -> None:
    policy = VECTORS["tag_directive_policy"]
    for vector in policy["accepted"]:
        assert parse_portable_yaml_with_locations(vector["yaml"]).value == vector["value"]

    for vector in policy["rejected"]:
        with pytest.raises(PortableValueError) as caught:
            parse_portable_yaml_with_locations(vector["yaml"])

        assert str(caught.value) == vector["message"]
        assert caught.value.path == vector["path"]
        assert (caught.value.line, caught.value.column) == (
            vector["line"],
            vector["column"],
        )

    for vector in policy["syntax_rejected"]:
        with pytest.raises(PortableYamlSyntaxError) as caught:
            parse_portable_yaml_with_locations(vector["yaml"])

        assert str(caught.value) == vector["message"]
        assert caught.value.path == vector["path"]
        assert (caught.value.line, caught.value.column) == (
            vector["line"],
            vector["column"],
        )


def test_explicit_numeric_tags_use_the_shared_portable_grammar() -> None:
    policy = VECTORS["explicit_numeric_tags"]
    for vector in policy["accepted"]:
        assert parse_portable_yaml_with_locations(vector["yaml"]).value == vector["value"]

    for vector in policy["rejected"]:
        with pytest.raises(PortableValueError) as caught:
            parse_portable_yaml_with_locations(vector["yaml"])

        assert str(caught.value) == vector["message"]
        assert caught.value.path == vector["path"]
        assert (caught.value.line, caught.value.column) == (
            vector["line"],
            vector["column"],
        )


def test_semantic_and_resource_failures_follow_shared_event_order() -> None:
    for vector in VECTORS["first_error_precedence"]:
        limits = replace(DEFAULT_VALIDATION_LIMITS, **vector.get("limits", {}))
        with pytest.raises(PortableValueError) as caught:
            parse_portable_yaml_with_locations(vector["yaml"], limits=limits)

        assert str(caught.value) == vector["message"]
        assert caught.value.path == vector["path"]
        assert (caught.value.line, caught.value.column) == (
            vector["line"],
            vector["column"],
        )


def test_document_and_empty_key_edges_use_shared_syntax_classifications() -> None:
    for vector in VECTORS["syntax_classification"]:
        error_type = PortableYamlSyntaxError if vector["kind"] == "syntax" else PortableValueError
        limits = replace(DEFAULT_VALIDATION_LIMITS, **vector.get("limits", {}))
        with pytest.raises(error_type) as caught:
            parse_portable_yaml_with_locations(vector["yaml"], limits=limits)

        assert str(caught.value) == vector["message"]
        assert caught.value.path == vector["path"]
        assert (caught.value.line, caught.value.column) == (
            vector["line"],
            vector["column"],
        )


def test_empty_null_nodes_use_shared_boundary_anchors() -> None:
    for vector in VECTORS["empty_null_anchors"]:
        parsed = parse_portable_yaml_with_locations(vector["yaml"])

        assert parsed.value == vector["value"]
        for expected in vector["anchors"]:
            node = parsed.source_map.node(expected["pointer"])
            assert node is not None
            assert _span(node.value) == expected["span"]


def test_empty_null_anchor_reaches_cli_diagnostics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vector = next(item for item in VECTORS["empty_null_anchors"] if "diagnostic" in item)
    source = tmp_path / "empty-null.yaml"
    source.write_bytes(vector["yaml"].encode())
    schema = tmp_path / "empty-null.schema.yaml"
    schema.write_text(
        (
            "$schema: https://json-schema.org/draft/2020-12/schema\n"
            "type: object\n"
            "properties:\n"
            "  values:\n"
            "    type: array\n"
            "    items: {type: string}\n"
            "required: [values]\n"
        ),
        encoding="utf-8",
    )

    exit_code = softschema_main(
        [
            "validate",
            str(source),
            "--profile",
            "pure-yaml",
            "--contract",
            "example:Value/v1",
            "--schema",
            str(schema),
            "--format",
            "jsonl",
        ]
    )

    captured = capsys.readouterr()
    diagnostic = json.loads(captured.out)["result"]["diagnostics"][0]
    assert exit_code == 1
    assert captured.err == ""
    assert {
        "path": diagnostic["path"],
        "line": diagnostic["line"],
        "column": diagnostic["column"],
    } == vector["diagnostic"]


def test_coded_yaml_parser_error_is_a_cli_parse_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vector = VECTORS["composer_syntax_errors"][0]
    source = tmp_path / "coded-parser-error.yaml"
    source.write_text(vector["yaml"], encoding="utf-8", newline="")

    exit_code = softschema_main(
        [
            "validate",
            str(source),
            "--profile",
            "pure-yaml",
            "--contract",
            "example:Value/v1",
        ]
    )

    captured = capsys.readouterr()
    record = json.loads(captured.out)
    assert exit_code == vector["cli"]["exit_code"]
    assert captured.err == ""
    assert record["kind"] == vector["cli"]["kind"]
    assert record["reason"] == vector["cli"]["reason"]
    assert record["message"] == vector["cli"]["message"]
