from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest

import softschema.cli as cli
from softschema.cli import main as softschema_main

# Tests write Markdown docs with indented YAML frontmatter for readability;
# frontmatter_format accepts uniform leading indent across top-level keys,
# so the layout below mirrors test_core.py's style.

SAMPLE_MODEL_SPEC = "test_cli_model:Sample"
SAMPLE_MODEL_SOURCE = dedent(
    """
    from __future__ import annotations

    from pydantic import BaseModel, ConfigDict


    class Sample(BaseModel):
        model_config = ConfigDict(extra="forbid")

        name: str
        count: int


    NotAModel = "not a class"
    """
).lstrip()


@pytest.fixture
def model_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    module_path = tmp_path / "test_cli_model.py"
    module_path.write_text(SAMPLE_MODEL_SOURCE)
    monkeypatch.chdir(tmp_path)
    return module_path


def write_doc(path: Path, frontmatter_yaml: str, body: str = "# title\n\nbody.\n") -> None:
    path.write_text(f"---\n{frontmatter_yaml}\n---\n{body}")


def test_compile_writes_schema_and_exits_zero(
    tmp_path: Path, model_module: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "sample.schema.yaml"

    exit_code = softschema_main(
        [
            "compile",
            SAMPLE_MODEL_SPEC,
            "--out",
            str(out),
            "--contract",
            "test:Sample/v1",
            "--schema-id",
            "https://schemas.example/test/sample/v1",
        ]
    )

    assert exit_code == 0
    assert out.is_file()
    result = json.loads(capsys.readouterr().out)
    assert result["drift"] is False
    assert result["schema_sha256"] is not None
    assert "$id: https://schemas.example/test/sample/v1" in result["schema_yaml"]


@pytest.mark.parametrize(
    ("flag", "value", "message"),
    [
        ("--contract", "bad id", "contract ID"),
        ("--schema-id", "relative/schema", "schema ID"),
    ],
)
def test_compile_validates_identity_before_importing_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    flag: str,
    value: str,
    message: str,
) -> None:
    def must_not_load(_spec: str) -> type[BaseException]:
        pytest.fail("model import ran before identity validation")

    monkeypatch.setattr(cli, "_load_model", must_not_load)
    out = tmp_path / "must-not-exist.yaml"

    argv = ["compile", "ignored:Model", "--out", str(out), flag, value]
    if flag == "--schema-id":
        argv.extend(["--contract", "test:Sample/v1"])
    exit_code = softschema_main(argv)

    assert exit_code == 2
    assert message in capsys.readouterr().err
    assert not out.exists()


def test_compile_requires_contract_before_importing_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def must_not_load(_spec: str) -> Any:
        pytest.fail("model import ran before required contract validation")

    monkeypatch.setattr(cli, "_load_model", must_not_load)
    out = tmp_path / "must-not-exist.yaml"

    exit_code = softschema_main(["compile", "ignored:Model", "--out", str(out)])

    assert exit_code == 2
    assert "requires --contract" in capsys.readouterr().err
    assert not out.exists()


def test_validate_checks_explicit_contract_before_reading_document(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = softschema_main(
        ["validate", str(tmp_path / "must-not-be-read.md"), "--contract", "bad id"]
    )

    assert exit_code == 2
    assert "contract ID" in capsys.readouterr().err


def test_validate_rejects_an_unknown_profile_with_portable_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = softschema_main(
        ["validate", str(tmp_path / "must-not-be-read.yaml"), "--profile", "yaml"]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == "softschema validate: invalid profile: yaml\n"


def test_compile_check_returns_one_when_schema_missing(tmp_path: Path, model_module: Path) -> None:
    out = tmp_path / "missing.schema.yaml"

    exit_code = softschema_main(
        [
            "compile",
            SAMPLE_MODEL_SPEC,
            "--out",
            str(out),
            "--contract",
            "test:Sample/v1",
            "--check",
        ]
    )

    assert exit_code == 1
    assert not out.exists()


def test_compile_check_returns_zero_when_schema_matches(tmp_path: Path, model_module: Path) -> None:
    out = tmp_path / "sample.schema.yaml"
    softschema_main(
        [
            "compile",
            SAMPLE_MODEL_SPEC,
            "--out",
            str(out),
            "--contract",
            "test:Sample/v1",
        ]
    )

    exit_code = softschema_main(
        [
            "compile",
            SAMPLE_MODEL_SPEC,
            "--out",
            str(out),
            "--contract",
            "test:Sample/v1",
            "--check",
        ]
    )

    assert exit_code == 0


def test_compile_rejects_malformed_model_spec(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "sample.schema.yaml"

    exit_code = softschema_main(
        ["compile", "bad-spec", "--out", str(out), "--contract", "test:Sample/v1"]
    )

    assert exit_code == 2
    assert "module:Class" in capsys.readouterr().err


def test_compile_rejects_non_basemodel(
    tmp_path: Path, model_module: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "sample.schema.yaml"

    exit_code = softschema_main(
        [
            "compile",
            "test_cli_model:NotAModel",
            "--out",
            str(out),
            "--contract",
            "test:Sample/v1",
        ]
    )

    assert exit_code == 2
    assert "BaseModel" in capsys.readouterr().err


def test_inspect_reports_envelope_keys_and_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    doc = tmp_path / "doc.md"
    write_doc(
        doc,
        """
        softschema:
          contract: test:Sample/v1
          status: enforced
        sample:
          name: hello
          count: 1
        """,
    )

    exit_code = softschema_main(["inspect", str(doc)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["envelope_keys"] == ["sample"]
    assert output["metadata"]["contract"] == "test:Sample/v1"
    assert output["metadata"]["status"] == "enforced"


def test_docs_list_includes_copyable_example_topics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = softschema_main(["docs", "--list"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "guide" in output
    assert "spec" in output
    assert "example-artifact" in output
    assert "does not scaffold or mutate projects" in output


def test_docs_prints_bundled_guide(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = softschema_main(["docs", "guide"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "# softschema Guide" in output
    assert "language-neutral" in output
    assert "## Adopt One Existing Artifact" in output
    assert "## Define a Contract in Python or TypeScript" in output


def test_docs_prints_copyable_movie_artifact(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = softschema_main(["docs", "example-artifact"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "softschema:" in output
    assert "contract: example.movies:MoviePage/v1" in output
    assert "# Spirited Away (2001)" in output
    assert "| Rotten Tomatoes Critics | 96% Tomatometer | 225 reviews |" in output


def test_docs_prints_copyable_pure_yaml_artifact(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = softschema_main(["docs", "example-pure-yaml"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "softschema:" in output
    assert "format:" not in output
    assert "contract: example.movies:MoviePage/v1" in output
    assert "title: Spirited Away" in output
    assert "---" not in output


def test_docs_list_supports_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = softschema_main(["docs", "--list", "--json"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    topic_names = [topic["name"] for topic in output["topics"]]
    assert "guide" in topic_names
    assert "spec" in topic_names
    assert "example-artifact" in output["copyable_examples"]
    assert "example-pure-yaml" in output["copyable_examples"]
    assert output["scaffolding"] is False


def test_docs_topic_supports_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = softschema_main(["docs", "spec", "--json"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["name"] == "spec"
    assert output["path"] == "docs/softschema-spec.md"
    assert "# softschema Spec" in output["content"]


def test_help_points_agents_to_skill_install(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        softschema_main(["--help"])

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "IMPORTANT for agents" in output
    assert "repo root" in output
    assert "skill --install" in output
    assert "uvx --from 'softschema==0.2.2' softschema" in output
    assert "npx --yes softschema@0.2.2" in output
    assert "bunx --bun softschema@0.2.2" in output


def test_validate_help_documents_the_profile_and_default(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        softschema_main(["validate", "--help"])

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "Artifact storage profile: frontmatter-md or pure-yaml" in output
    assert "default: frontmatter-md" in output


def test_version_prints_installed_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        softschema_main(["--version"])

    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"softschema {cli._installed_version()}"


def test_doctor_reports_discovery_capabilities_as_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = softschema_main(["doctor", "--json"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    release = cli._release_metadata()
    assert output["protocol_version"] == release["discovery_protocol"]
    assert output["package"]["version"] == release["logical_version"]
    assert output["runtime"]["name"] == "python"
    assert output["capabilities"]["model_loaders"] == ["json-schema", "pydantic"]
    assert "validate" in output["capabilities"]["operations"]


def test_doctor_text_summarizes_versioned_capabilities(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = softschema_main(["doctor"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "softschema discovery protocol: 1" in output
    assert "runtime: python" in output
    assert "operations: compile, docs, doctor" in output
    assert "model loaders: json-schema, pydantic" in output
    assert "build: sha256:" in output


def test_skill_brief_points_agents_to_docs_and_rules(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = softschema_main(["skill", "--brief"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "softschema doctor --json" in output
    assert "docs --list" in output
    assert "Never parse Markdown" in output


def test_skill_brief_is_derived_from_source_skill(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = softschema_main(["skill", "--brief"])

    assert exit_code == 0
    assert capsys.readouterr().out == cli._brief_skill_text()


def test_skill_uses_capability_checked_pinned_runners(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = softschema_main(["skill"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "uvx --from 'softschema==0.2.2' softschema doctor --json" in output
    assert "npx --yes softschema@0.2.2 doctor --json" in output
    assert "bunx --bun softschema@0.2.2 doctor --json" in output
    assert "Qualify a Runner" in output
    assert "validate --help" in output
    assert "installed or upgraded to a release" in output
    assert "$SS" not in output
    assert "@latest" not in output


def test_skill_install_creates_both_mirrors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()

    exit_code = softschema_main(["skill", "--install"])

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert {f["path"] for f in summary["files"]} == {
        ".agents/skills/softschema/SKILL.md",
        ".claude/skills/softschema/SKILL.md",
    }
    assert all(f["status"] == "created" for f in summary["files"])

    agents = (tmp_path / ".agents/skills/softschema/SKILL.md").read_text(encoding="utf-8")
    claude = (tmp_path / ".claude/skills/softschema/SKILL.md").read_text(encoding="utf-8")
    assert agents == claude
    assert "DO NOT EDIT format=f01: written by `softschema skill --install`" in agents


def test_skill_install_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    softschema_main(["skill", "--install"])
    capsys.readouterr()

    exit_code = softschema_main(["skill", "--install"])

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert all(f["status"] == "unchanged" for f in summary["files"])


def test_skill_install_text_dry_run_uses_explicit_agent_without_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()

    exit_code = softschema_main(
        [
            "skill",
            "--install",
            "--dry-run",
            "--agent",
            "cursor",
            "--agent",
            "roo",
            "--text",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.replace("\\", "/")
    assert "softschema skill install (project, agent-targets-v1)" in output
    assert ".cursor/skills/softschema/SKILL.md" in output
    assert ".roo/skills/softschema/SKILL.md" in output
    assert ".agents/skills" not in output
    assert not (tmp_path / ".cursor").exists()
    assert not (tmp_path / ".roo").exists()


def test_skill_install_ambiguous_location_is_exit_two_without_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = softschema_main(["skill", "--install"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "scope is ambiguous outside a Git repository" in captured.err
    assert not (tmp_path / ".agents").exists()
    assert not (tmp_path / ".claude").exists()


def test_validate_overrides_apply_when_frontmatter_lacks_metadata(
    tmp_path: Path, model_module: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "sample.schema.yaml"
    softschema_main(
        ["compile", SAMPLE_MODEL_SPEC, "--out", str(out), "--contract", "test:Sample/v1"]
    )
    capsys.readouterr()
    doc = tmp_path / "doc.md"
    write_doc(doc, "sample:\n  name: hello\n  count: 1\n")

    exit_code = softschema_main(
        [
            "validate",
            str(doc),
            "--model",
            SAMPLE_MODEL_SPEC,
            "--schema",
            str(out),
            "--contract",
            "test:Sample/v1",
            "--envelope",
            "sample",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["contract_id"] == "test:Sample/v1"
    assert output["values"] == {"name": "hello", "count": 1}


def test_validate_exits_two_when_contract_missing(
    tmp_path: Path, model_module: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    doc = tmp_path / "doc.md"
    write_doc(doc, "sample:\n  name: hello\n  count: 1\n")

    exit_code = softschema_main(["validate", str(doc), "--model", SAMPLE_MODEL_SPEC])

    assert exit_code == 2
    assert "--contract" in capsys.readouterr().err


def test_validate_without_model_or_schema_is_a_metadata_only_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A soft-stage artifact (contract, no schema or model yet) validates its
    metadata and envelope; the structural and semantic layers report skipped."""
    doc = tmp_path / "doc.md"
    write_doc(
        doc,
        """
        softschema:
          contract: test:Sample/v1
        sample:
          name: hello
          count: 1
        """,
    )

    exit_code = softschema_main(["validate", str(doc)])

    assert exit_code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["structural"]["skipped_reason"] == "no_schema"
    assert result["semantic"]["skipped_reason"] == "no_semantic_model"


def test_metadata_only_validate_still_rejects_malformed_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    doc = tmp_path / "doc.md"
    write_doc(
        doc,
        """
        softschema:
          contract: test:Sample/v1
          bogus: 1
        sample:
          name: hello
        """,
    )

    exit_code = softschema_main(["validate", str(doc)])

    assert exit_code == 2
    assert "softschema validate:" in capsys.readouterr().err


def test_validate_exits_two_on_ambiguous_envelope(
    tmp_path: Path, model_module: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    doc = tmp_path / "doc.md"
    write_doc(
        doc,
        """
        softschema:
          contract: test:Sample/v1
        sample:
          name: hello
          count: 1
        other:
          name: world
          count: 2
        """,
    )

    exit_code = softschema_main(["validate", str(doc), "--model", SAMPLE_MODEL_SPEC])

    assert exit_code == 2
    assert "--envelope" in capsys.readouterr().err


def test_validate_exits_one_when_payload_fails_model(tmp_path: Path, model_module: Path) -> None:
    out = tmp_path / "sample.schema.yaml"
    softschema_main(
        ["compile", SAMPLE_MODEL_SPEC, "--out", str(out), "--contract", "test:Sample/v1"]
    )
    doc = tmp_path / "doc.md"
    write_doc(
        doc,
        """
        softschema:
          contract: test:Sample/v1
        sample:
          name: hello
          count: not-an-int
        """,
    )

    exit_code = softschema_main(
        ["validate", str(doc), "--model", SAMPLE_MODEL_SPEC, "--schema", str(out)]
    )

    assert exit_code == 1


# ---------------------------------------------------------------------------
# Error-boundary regression tests (Phase 1 remediation)
# ---------------------------------------------------------------------------


def test_validate_missing_file_exits_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing artifact file must exit 2 with a stable input-error record."""
    missing = tmp_path / "does-not-exist.md"
    schema = tmp_path / "dummy.schema.yaml"
    schema.write_text("{}")

    exit_code = softschema_main(["validate", str(missing), "--schema", str(schema)])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "kind": "input_error",
        "reason": "not_found",
        "message": "artifact path does not exist",
        "source": str(missing),
    }


def test_validate_bad_model_module_exits_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A --model pointing to a nonexistent module must exit 2."""
    doc = tmp_path / "doc.md"
    write_doc(doc, "sample:\n  name: hello\n  count: 1\n")

    exit_code = softschema_main(
        ["validate", str(doc), "--model", "nonexistent_module:Foo", "--contract", "x"]
    )

    assert exit_code == 2
    err = capsys.readouterr().err
    assert "softschema validate:" in err
    assert "Traceback" not in err


def test_inspect_missing_file_exits_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Missing file for inspect must exit 2."""
    missing = tmp_path / "does-not-exist.md"

    exit_code = softschema_main(["inspect", str(missing)])

    assert exit_code == 2
    err = capsys.readouterr().err
    assert "softschema inspect:" in err
    assert "Traceback" not in err


def test_inspect_malformed_softschema_block_exits_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A softschema block that is a list instead of a mapping must exit 2."""
    doc = tmp_path / "doc.md"
    doc.write_text("---\nsoftschema: [1, 2]\n---\n# title\n")

    exit_code = softschema_main(["inspect", str(doc)])

    assert exit_code == 2
    err = capsys.readouterr().err
    assert "softschema inspect:" in err
    assert "Traceback" not in err


def test_run_cmd_surfaces_internal_bugs() -> None:
    """TypeError/KeyError signal internal bugs and must surface, not be masked as exit 2."""

    def raise_type(_args: object) -> int:
        raise TypeError("internal bug")

    def raise_key(_args: object) -> int:
        raise KeyError("missing")

    with pytest.raises(TypeError):
        cli._run_cmd("validate", raise_type, argparse.Namespace())
    with pytest.raises(KeyError):
        cli._run_cmd("validate", raise_key, argparse.Namespace())


def test_run_cmd_reports_usage_error_as_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    """A UsageError (and any ValueError) is a user mistake: clean one-liner, exit 2."""

    def raise_usage(_args: object) -> int:
        raise cli.UsageError("bad flag")

    exit_code = cli._run_cmd("validate", raise_usage, argparse.Namespace())

    assert exit_code == 2
    assert "softschema validate: bad flag" in capsys.readouterr().err


def test_prime_prints_skill_and_docs_index(capsys: pytest.CaptureFixture[str]) -> None:
    """`prime` restores full agent context: skill operating rules + the bundled docs index."""
    exit_code = softschema_main(["prime"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "softschema" in out  # skill content
    assert "Available softschema docs:" in out  # docs index
    assert "Run `softschema docs <topic>`" in out
