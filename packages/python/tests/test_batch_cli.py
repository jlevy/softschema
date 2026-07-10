from __future__ import annotations

import json
import os
from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest
from jsonschema.validators import validator_for
from pydantic import BaseModel

import softschema.cli as cli
from softschema.cli import main as softschema_main
from softschema.runtime.discovery import DISCOVERY_MAX_DEPTH

ROOT = Path(__file__).parents[3]
SOURCE_SEPARATOR_VECTORS: dict[str, Any] = json.loads(
    (ROOT / "tests/value-domain/source-separator-vectors.json").read_text(encoding="utf-8")
)
EXTRA_PROPERTY_VECTORS: dict[str, Any] = json.loads(
    (ROOT / "tests/diagnostics/extra-property-location-vectors.json").read_text(encoding="utf-8")
)


def _artifact(path: Path, payload: str, *, contract: bool = False) -> None:
    metadata = "softschema: test.batch:Record/v1\n" if contract else ""
    path.write_text(f"---\n{metadata}record:\n{payload}---\nbody\n", encoding="utf-8")


def _schema(path: Path) -> None:
    path.write_text(
        dedent(
            """
            $schema: https://json-schema.org/draft/2020-12/schema
            type: object
            required: [name, count]
            properties:
              name: {type: string}
              count: {type: integer}
            additionalProperties: false
            """
        ).lstrip(),
        encoding="utf-8",
    )


def _batch_args(directory: Path, schema: Path, *extra: str) -> list[str]:
    return [
        "validate",
        str(directory),
        "--recursive",
        "--contract",
        "test.batch:Record/v1",
        "--envelope",
        "record",
        "--schema",
        str(schema),
        *extra,
    ]


def test_batch_json_reports_partial_success_and_payload_locations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    schema = tmp_path / "record.schema.yaml"
    _schema(schema)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    _artifact(artifacts / "a-valid.md", "  name: Valid\n  count: 2\n")
    _artifact(artifacts / "b-invalid.md", "  name: Invalid\n  count: nope\n")
    monkeypatch.chdir(tmp_path)

    exit_code = softschema_main(_batch_args(artifacts, schema))

    captured = capsys.readouterr()
    assert captured.err == ""
    assert exit_code == 1
    aggregate = json.loads(captured.out)
    assert aggregate["format"] == "diagnostic-v1"
    assert aggregate["summary"] == {
        "exit_code": 1,
        "input_failed": 0,
        "passed": 1,
        "total": 2,
        "validation_failed": 1,
    }
    assert [result["input"]["source"] for result in aggregate["results"]] == [
        "artifacts/a-valid.md",
        "artifacts/b-invalid.md",
    ]
    diagnostic = aggregate["results"][1]["diagnostics"][0]
    assert diagnostic["path"] == "/record/count"
    assert (diagnostic["line"], diagnostic["column"]) == (4, 10)


def test_batch_jsonl_has_one_self_describing_line_per_result_and_no_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    schema = tmp_path / "record.schema.yaml"
    _schema(schema)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    _artifact(artifacts / "a.md", "  name: A\n  count: 1\n")
    _artifact(artifacts / "b.md", "  name: B\n  count: no\n")
    monkeypatch.chdir(tmp_path)

    exit_code = softschema_main(_batch_args(artifacts, schema, "--format", "jsonl"))

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    records = [json.loads(line) for line in captured.out.removesuffix("\n").split("\n")]
    assert len(records) == 2
    assert all(record["format"] == "diagnostic-v1" for record in records)
    assert all("result" in record and "summary" not in record for record in records)


def test_jsonl_reports_shared_nonportable_source_separator_location(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vector = SOURCE_SEPARATOR_VECTORS["literal_cases"][1]
    source = tmp_path / "artifact.yaml"
    source.write_bytes(vector["yaml"].encode())
    monkeypatch.chdir(tmp_path)

    exit_code = softschema_main(
        ["validate", "artifact.yaml", "--profile", "pure-yaml", "--format", "jsonl"]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    result = json.loads(captured.out)["result"]
    expected = SOURCE_SEPARATOR_VECTORS["artifact_error"]
    assert result["input"] == {
        "kind": "parse_error",
        "reason": expected["reason"],
        "message": expected["message"],
        "source": "artifact.yaml",
        "path": expected["path"],
        "line": vector["line"],
        "column": vector["column"],
    }
    assert result["diagnostics"][0] == {
        "category": "parse",
        "rule_id": "softschema.parse_error.value_domain",
        "severity": "error",
        "message": expected["message"],
        "source": "artifact.yaml",
        "path": expected["path"],
        "line": vector["line"],
        "column": vector["column"],
    }


@pytest.mark.parametrize(
    "vector",
    EXTRA_PROPERTY_VECTORS["cases"],
    ids=lambda item: item["id"],
)
def test_extra_property_diagnostic_anchors_shared_escaped_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    vector: dict[str, Any],
) -> None:
    (tmp_path / "artifact.yaml").write_text(EXTRA_PROPERTY_VECTORS["artifact"], encoding="utf-8")
    (tmp_path / "schema.yaml").write_text(vector["schema"], encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = softschema_main(
        [
            "validate",
            "artifact.yaml",
            "--profile",
            "pure-yaml",
            "--contract",
            EXTRA_PROPERTY_VECTORS["contract"],
            "--envelope",
            EXTRA_PROPERTY_VECTORS["envelope"],
            "--schema",
            "schema.yaml",
            "--format",
            "jsonl",
        ]
    )

    assert exit_code == 1
    record = json.loads(capsys.readouterr().out)["result"]
    error = record["validation"]["structural"]["errors"][0]
    assert set(error) == {
        "kind",
        "path",
        "validator",
        "validator_value",
        "value",
        "message",
    }
    expected = EXTRA_PROPERTY_VECTORS["expected"]
    assert record["diagnostics"] == [
        {
            "category": "structural",
            "rule_id": f"softschema.schema_violation.{vector['validator'].lower()}",
            "severity": "error",
            "message": expected["message"],
            "source": "artifact.yaml",
            "path": expected["path"],
            "line": expected["line"],
            "column": expected["column"],
        }
    ]


def test_recursive_no_matches_is_fail_closed_input_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    monkeypatch.chdir(tmp_path)

    exit_code = softschema_main(["validate", "artifacts", "--recursive"])

    assert exit_code == 2
    result = json.loads(capsys.readouterr().out)
    assert result["summary"]["exit_code"] == 2
    assert result["results"][0]["input"] == {
        "kind": "input_error",
        "message": "artifact directory contains no matching files",
        "reason": "no_matches",
        "source": "artifacts",
    }


def test_recursive_discovery_limit_discards_operand_matches_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    _artifact(root / "a-early.md", "  name: Early\n  count: 1\n")
    current = root
    for index in range(DISCOVERY_MAX_DEPTH + 1):
        current /= f"d{index:03d}"
        current.mkdir()
    _artifact(tmp_path / "after.md", "  name: After\n  count: 2\n")
    monkeypatch.chdir(tmp_path)

    exit_code = softschema_main(["validate", "artifacts", "after.md", "--recursive"])

    assert exit_code == 2
    aggregate = json.loads(capsys.readouterr().out)
    limit_source = "artifacts/" + "/".join(
        f"d{index:03d}" for index in range(DISCOVERY_MAX_DEPTH + 1)
    )
    assert [result["input"] for result in aggregate["results"]] == [
        {
            "kind": "input_error",
            "message": "artifact discovery limit exceeded",
            "reason": "discovery_limit",
            "source": limit_source,
        },
        {
            "kind": "artifact_input",
            "ok": True,
            "profile": "frontmatter-md",
            "source": "after.md",
            "values": {"record": {"count": 2, "name": "After"}},
        },
    ]


def test_batch_deduplicates_explicit_file_and_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact = tmp_path / "artifact.md"
    alias = tmp_path / "alias.md"
    _artifact(artifact, "  name: A\n  count: 1\n", contract=True)
    try:
        alias.symlink_to(artifact)
    except OSError:
        pytest.skip("symlinks are unavailable")
    monkeypatch.chdir(tmp_path)

    exit_code = softschema_main(["validate", "artifact.md", "alias.md"])

    assert exit_code == 0
    aggregate = json.loads(capsys.readouterr().out)
    assert aggregate["summary"]["total"] == 1
    assert aggregate["results"][0]["input"]["source"] == "artifact.md"


def test_batch_loads_the_semantic_model_once_after_all_bindings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class Sample(BaseModel):
        name: str
        count: int

    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    _artifact(first, "  name: A\n  count: 1\n")
    _artifact(second, "  name: B\n  count: 2\n")
    loads: list[str] = []

    def load_once(spec: str) -> type[BaseModel]:
        loads.append(spec)
        return Sample

    monkeypatch.setattr(cli, "_load_model", load_once)

    exit_code = softschema_main(
        [
            "validate",
            str(first),
            str(second),
            "--contract",
            "test.batch:Record/v1",
            "--envelope",
            "record",
            "--model",
            "trusted:Sample",
        ]
    )

    assert exit_code == 0
    assert loads == ["trusted:Sample"]
    assert json.loads(capsys.readouterr().out)["summary"]["passed"] == 2


def test_binding_failure_does_not_abort_remaining_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    unbound = tmp_path / "a-unbound.md"
    bound = tmp_path / "b-bound.md"
    _artifact(unbound, "  name: A\n  count: 1\n")
    _artifact(bound, "  name: B\n  count: 2\n", contract=True)
    monkeypatch.chdir(tmp_path)

    exit_code = softschema_main(["validate", "a-unbound.md", "b-bound.md"])

    assert exit_code == 1
    aggregate = json.loads(capsys.readouterr().out)
    assert [result["outcome"] for result in aggregate["results"]] == [
        "validation_failed",
        "passed",
    ]
    binding = aggregate["results"][0]
    assert binding["validation"] is None
    assert binding["diagnostics"][0]["rule_id"] == "softschema.artifact.contract_unknown"


def test_single_explicit_file_keeps_exact_legacy_bytes_with_harmless_batch_flags(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact = tmp_path / "artifact.md"
    _artifact(artifact, "  name: A\n  count: 1\n", contract=True)

    assert softschema_main(["validate", str(artifact)]) == 0
    legacy = capsys.readouterr()
    assert softschema_main(["validate", str(artifact), "--recursive", "--format", "json"]) == 0
    harmless = capsys.readouterr()

    assert harmless == legacy
    assert "diagnostic-v1" not in legacy.out


def test_invalid_glob_fails_before_reading_or_importing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def must_not_load(_spec: str) -> Any:
        pytest.fail("model import ran before request validation")

    monkeypatch.setattr(cli, "_load_model", must_not_load)

    exit_code = softschema_main(
        [
            "validate",
            str(tmp_path / "must-not-be-read"),
            "--recursive",
            "--include",
            "bad/**tail",
            "--model",
            "ignored:Model",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "partial_globstar" in captured.err


def test_directory_with_one_result_and_duplicate_operands_stay_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    _artifact(artifacts / "only.md", "  name: A\n  count: 1\n", contract=True)
    monkeypatch.chdir(tmp_path)

    assert softschema_main(["validate", "artifacts", "--recursive"]) == 0
    assert json.loads(capsys.readouterr().out)["format"] == "diagnostic-v1"
    assert softschema_main(["validate", "artifacts/only.md", "artifacts/only.md"]) == 0
    duplicate = json.loads(capsys.readouterr().out)
    assert duplicate["format"] == "diagnostic-v1"
    assert duplicate["summary"]["total"] == 1


def test_unsafe_nonfiles_never_enter_the_legacy_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    directory = tmp_path / "directory"
    directory.mkdir()
    directory_alias = tmp_path / "directory-alias.md"
    try:
        directory_alias.symlink_to(directory, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are unavailable")
    monkeypatch.chdir(tmp_path)

    assert softschema_main(["validate", "directory-alias.md"]) == 2
    symlink_result = json.loads(capsys.readouterr().out)
    assert symlink_result["format"] == "diagnostic-v1"
    assert symlink_result["results"][0]["input"]["reason"] == "unreadable"

    if hasattr(os, "mkfifo"):
        fifo = tmp_path / "artifact.md"
        os.mkfifo(fifo)
        assert softschema_main(["validate", "artifact.md"]) == 2
        fifo_result = json.loads(capsys.readouterr().out)
        assert fifo_result["format"] == "diagnostic-v1"
        assert fifo_result["results"][0]["input"]["reason"] == "unreadable"


def test_broken_symlink_and_missing_file_keep_legacy_not_found_compatibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    broken = tmp_path / "broken.md"
    try:
        broken.symlink_to(tmp_path / "missing-target.md")
    except OSError:
        pytest.skip("symlinks are unavailable")

    for source in ("broken.md", "missing.md"):
        assert softschema_main(["validate", source, "--contract", "test.batch:Record/v1"]) == 2
        record = json.loads(capsys.readouterr().out)
        assert record == {
            "kind": "input_error",
            "message": "artifact path does not exist",
            "reason": "not_found",
            "source": source,
        }


def test_mixed_parse_input_and_valid_results_apply_exit_two_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    valid = tmp_path / "valid.md"
    malformed = tmp_path / "malformed.md"
    _artifact(valid, "  name: A\n  count: 1\n", contract=True)
    malformed.write_text("---\nrecord: [unterminated\n---\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = softschema_main(
        [
            "validate",
            "valid.md",
            "malformed.md",
            "missing.md",
            "--contract",
            "test.batch:Record/v1",
            "--envelope",
            "record",
        ]
    )

    assert exit_code == 2
    aggregate = json.loads(capsys.readouterr().out)
    assert aggregate["summary"] == {
        "exit_code": 2,
        "input_failed": 1,
        "passed": 1,
        "total": 3,
        "validation_failed": 1,
    }
    assert [result["outcome"] for result in aggregate["results"]] == [
        "passed",
        "validation_failed",
        "input_failed",
    ]


def test_recursive_profile_include_and_exclude_filters_are_applied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifacts = tmp_path / "artifacts"
    keep = artifacts / "keep"
    drop = artifacts / "drop"
    keep.mkdir(parents=True)
    drop.mkdir()
    _artifact(keep / "selected.md", "  name: A\n  count: 1\n", contract=True)
    _artifact(keep / "excluded.md", "  name: B\n  count: 2\n", contract=True)
    _artifact(drop / "other.md", "  name: C\n  count: 3\n", contract=True)
    (keep / "wrong-profile.yaml").write_text("name: ignored\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = softschema_main(
        [
            "validate",
            "artifacts",
            "--recursive",
            "--include",
            "keep/**",
            "--exclude",
            "**/excluded.md",
        ]
    )

    assert exit_code == 0
    aggregate = json.loads(capsys.readouterr().out)
    assert [result["input"]["source"] for result in aggregate["results"]] == [
        "artifacts/keep/selected.md"
    ]


def test_explicit_schema_diagnostic_has_schema_source_location_and_valid_sarif(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact = tmp_path / "artifact.md"
    schema = tmp_path / "bad.schema.yaml"
    _artifact(artifact, "  name: A\n  count: 1\n", contract=True)
    schema.write_text(
        "$schema: https://example.invalid/schema\ntype: object\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    argv = [
        "validate",
        "artifact.md",
        "--envelope",
        "record",
        "--schema",
        "bad.schema.yaml",
        "--format",
        "sarif",
    ]

    assert softschema_main(argv) == 1

    sarif = json.loads(capsys.readouterr().out)
    result = sarif["runs"][0]["results"][0]
    assert result["properties"]["softschemaSchemaSource"] == "bad.schema.yaml"
    assert result["properties"]["softschemaSchemaPath"] == "/$schema"
    assert result["locations"][0]["physicalLocation"]["region"] == {
        "startColumn": 10,
        "startLine": 1,
    }
    schema_document = json.loads(
        (
            Path(__file__).parents[3]
            / "tests/diagnostics/fixtures/sarif-schema-2.1.0-errata01.json"
        ).read_text(encoding="utf-8")
    )
    validator_class = validator_for(schema_document)
    validator_class.check_schema(schema_document)
    validator_class(schema_document).validate(sarif)


def test_metadata_schema_source_is_resolved_relative_to_the_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    documents = tmp_path / "documents"
    documents.mkdir()
    (documents / "bad.schema.yaml").write_text(
        "$schema: https://example.invalid/schema\ntype: object\n",
        encoding="utf-8",
    )
    (documents / "artifact.md").write_text(
        dedent(
            """
            ---
            softschema:
              contract: test.batch:Record/v1
              schema: bad.schema.yaml
              envelope: record
            record:
              name: A
              count: 1
            ---
            body
            """
        ).lstrip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert softschema_main(["validate", "documents/artifact.md", "--format", "jsonl"]) == 1

    record = json.loads(capsys.readouterr().out)
    diagnostic = record["result"]["diagnostics"][0]
    assert diagnostic["schema_source"] == "documents/bad.schema.yaml"
    assert (diagnostic["line"], diagnostic["column"]) == (1, 10)


def test_metadata_schema_symlink_cannot_escape_document_and_working_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = tmp_path / "workspace"
    documents = workspace / "documents"
    outside = tmp_path / "outside"
    documents.mkdir(parents=True)
    outside.mkdir()
    (outside / "outside.schema.yaml").write_text("type: object\n", encoding="utf-8")
    try:
        (documents / "linked.schema.yaml").symlink_to(outside / "outside.schema.yaml")
    except OSError:
        pytest.skip("symlinks are unavailable")
    (documents / "artifact.md").write_text(
        dedent(
            """
            ---
            softschema:
              contract: test.batch:Record/v1
              schema: linked.schema.yaml
              envelope: record
            record:
              name: A
              count: 1
            ---
            body
            """
        ).lstrip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(workspace)

    assert softschema_main(["validate", "documents/artifact.md", "--format", "jsonl"]) == 1

    record = json.loads(capsys.readouterr().out)
    assert record["result"]["diagnostics"][0] == {
        "category": "structural",
        "column": 11,
        "line": 4,
        "message": "compiled schema is unavailable",
        "path": "/softschema/schema",
        "rule_id": "softschema.artifact.schema_missing",
        "severity": "error",
        "source": "documents/artifact.md",
    }


def test_closed_output_pipe_is_a_clean_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def closed_pipe(_args: Any) -> int:
        raise BrokenPipeError

    monkeypatch.setattr(cli, "_validate_cmd", closed_pipe)

    assert softschema_main(["validate", "unused.md"]) == 0
