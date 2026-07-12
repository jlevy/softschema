from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import dedent

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
        ["compile", SAMPLE_MODEL_SPEC, "--out", str(out), "--contract", "test:Sample/v1"]
    )

    assert exit_code == 0
    assert out.is_file()
    result = json.loads(capsys.readouterr().out)
    assert result["drift"] is False
    assert result["schema_sha256"] is not None


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
        ["compile", SAMPLE_MODEL_SPEC, "--out", str(out), "--contract", "test:Sample/v1"]
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
    assert "## Playbook: Add Python Validation" in output


def test_docs_prints_copyable_movie_artifact(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = softschema_main(["docs", "example-artifact"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "softschema:" in output
    assert "contract: example.movies:MoviePage/v1" in output
    assert "# Spirited Away (2001)" in output
    assert "| Rotten Tomatoes Critics | 96% Tomatometer | 225 reviews |" in output


def test_docs_list_supports_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = softschema_main(["docs", "--list", "--json"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    topic_names = [topic["name"] for topic in output["topics"]]
    assert "guide" in topic_names
    assert "spec" in topic_names
    assert "example-artifact" in output["copyable_examples"]
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
    assert "uvx softschema@latest" in output
    assert "npx -y softschema@latest" in output


def test_version_prints_installed_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        softschema_main(["--version"])

    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"softschema {cli._installed_version()}"


def test_doctor_reports_available_runners_as_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    paths = {
        "softschema": "/usr/local/bin/softschema",
        "uvx": "/opt/homebrew/bin/uvx",
        "npx": None,
    }
    monkeypatch.setattr(cli, "_find_runner", lambda name: paths[name])

    exit_code = softschema_main(["doctor", "--json"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["version"] == cli._installed_version()
    assert output["recommended_invocation"] == "softschema"
    assert output["runners"] == [
        {"name": "softschema", "available": True, "path": "/usr/local/bin/softschema"},
        {"name": "uvx", "available": True, "path": "/opt/homebrew/bin/uvx"},
        {"name": "npx", "available": False, "path": None},
    ]


def test_doctor_text_tells_user_how_to_recover_when_no_runner_exists(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_find_runner", lambda _name: None)

    exit_code = softschema_main(["doctor"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "softschema version:" in output
    assert "recommended invocation: unavailable" in output
    assert "Install uv or Node" in output


def test_skill_brief_points_agents_to_docs_and_rules(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = softschema_main(["skill", "--brief"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "$SS docs guide" in output
    assert "$SS docs spec" in output
    assert "Do not parse Markdown body prose or tables" in output


def test_skill_brief_is_derived_from_source_skill(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = softschema_main(["skill", "--brief"])

    assert exit_code == 0
    assert capsys.readouterr().out == cli._brief_skill_text()


def test_skill_uses_latest_runner(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = softschema_main(["skill"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "uvx softschema@latest" in output
    assert "npx -y softschema@latest" in output
    assert "Pick One Runner" in output
    assert "$SS docs guide" in output


def test_skill_install_creates_both_mirrors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = softschema_main(
        ["skill", "--install", "--scope", "project", "--agent", "portable", "--agent", "claude"]
    )

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
    assert "DO NOT EDIT format=f02:" in agents
    assert "source-sha256" not in agents


def test_skill_install_is_idempotent_and_refreshes_managed_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    args = ["skill", "--install", "--scope", "project", "--agent", "portable", "--agent", "claude"]
    softschema_main(args)
    capsys.readouterr()

    exit_code = softschema_main(args)

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert all(f["status"] == "unchanged" for f in summary["files"])

    target = tmp_path / ".agents/skills/softschema/SKILL.md"
    target.write_text(target.read_text().replace("# softschema Skill", "# local edit"))
    assert softschema_main(args) == 0
    summary = json.loads(capsys.readouterr().out)
    assert {f["path"]: f["status"] for f in summary["files"]} == {
        ".agents/skills/softschema/SKILL.md": "updated",
        ".claude/skills/softschema/SKILL.md": "unchanged",
    }
    assert "# softschema Skill" in target.read_text()


def test_skill_install_dry_run_and_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    args = ["skill", "--install", "--scope", "project", "--agent", "portable"]
    assert softschema_main([*args, "--dry-run"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["files"][0]["status"] == "would_create"
    assert not (tmp_path / summary["files"][0]["path"]).exists()

    target = tmp_path / ".agents/skills/softschema/SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("unmanaged\n")
    assert softschema_main(args) == 2
    assert target.read_text() == "unmanaged\n"


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
    """Missing artifact file must exit 2 with a clean message, no traceback."""
    missing = tmp_path / "does-not-exist.md"
    schema = tmp_path / "dummy.schema.yaml"
    schema.write_text("{}")

    exit_code = softschema_main(["validate", str(missing), "--schema", str(schema)])

    assert exit_code == 2
    err = capsys.readouterr().err
    assert "softschema validate:" in err
    assert "Traceback" not in err


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
