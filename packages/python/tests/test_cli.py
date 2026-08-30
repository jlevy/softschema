from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import dedent

import pytest

import softschema.cli as cli
from softschema.cli import main as softschema_main
from softschema.models import SchemaProfile

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


# --- Profile detection on the repair path -------------------------------------------
#
# `--repair` must reach the same read verdict as plain `validate`. It once did not: a
# document that opened a frontmatter fence and never closed it was detected as pure-yaml,
# its leading `---` was consumed as a YAML document-start marker, and the repair path
# reported `valid` for a file plain `validate` could not open at all. See
# docs/project/reviews/review-2026-08-30-validate-repair-e2e.md, Finding 1.

MINI_SCHEMA = dedent(
    """
    $schema: https://json-schema.org/draft/2020-12/schema
    type: object
    additionalProperties: false
    required: [name]
    properties:
      name: {type: string}
    """
).lstrip()

_FRONTMATTER_BODY = dedent(
    """
    softschema:
      contract: test.detect:Doc/v1
      schema: mini.schema.yaml
      envelope: rec
      status: enforced
    rec:
      name: Acme
    """
).strip()


def _detect_case(tmp_path: Path, name: str, text: str) -> Path:
    (tmp_path / "mini.schema.yaml").write_text(MINI_SCHEMA)
    path = tmp_path / name
    path.write_text(text)
    return path


def test_detect_profile_keeps_an_unterminated_fence_on_frontmatter_md(tmp_path: Path) -> None:
    path = _detect_case(tmp_path, "unterminated.md", f"---\n{_FRONTMATTER_BODY}\n")
    assert cli._detect_profile(path) is SchemaProfile.frontmatter_md


def test_unterminated_fence_is_unreadable_on_both_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _detect_case(tmp_path, "unterminated.md", f"---\n{_FRONTMATTER_BODY}\n")

    # Plain validate refuses the document, naming the missing delimiter.
    assert softschema_main(["validate", str(path)]) == 2
    plain = capsys.readouterr().err
    assert "Delimiter `---` for end of frontmatter not found" in plain

    # `repair` must refuse it too, and name the same cause. It reports rather than
    # raises: an unreadable document is this command's normal input, so the diagnostic
    # goes in a record where the agent that wrote the file can act on it.
    assert softschema_main(["repair", str(path), "--check"]) == 1
    record = json.loads(capsys.readouterr().out)["structural"]["errors"][0]
    assert record["kind"] == "yaml_parse_error"
    assert "Delimiter `---` for end of frontmatter not found" in record["message"]
    assert "has no YAML frontmatter" not in record["message"]


def test_terminated_fence_still_validates_on_both_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _detect_case(tmp_path, "terminated.md", f"---\n{_FRONTMATTER_BODY}\n---\n# Body\n")
    assert cli._detect_profile(path) is SchemaProfile.frontmatter_md
    for argv in (["validate", str(path)], ["repair", str(path), "--check"]):
        assert softschema_main(argv) == 0
        assert json.loads(capsys.readouterr().out)["outcome"] == "valid"


def test_detect_profile_still_reads_a_fenceless_document_as_pure_yaml(tmp_path: Path) -> None:
    # The fix narrows what counts as "fenceless"; a document that never opened a fence is
    # still pure-yaml, which is the rule the narrowing must not break.
    path = _detect_case(tmp_path, "fenceless.md", f"{_FRONTMATTER_BODY}\n")
    assert cli._detect_profile(path) is SchemaProfile.pure_yaml


def test_detect_profile_keeps_a_yaml_file_with_a_document_start_marker_pure(
    tmp_path: Path,
) -> None:
    # A `*.yaml` file may legitimately open with `---` as a YAML document-start marker.
    # The suffix rule answers first, so the fence check never sees it.
    path = _detect_case(tmp_path, "record.yaml", f"---\n{_FRONTMATTER_BODY}\n")
    assert cli._detect_profile(path) is SchemaProfile.pure_yaml


# --- Fences at end of file --------------------------------------------------------
#
# A final line with no trailing newline is a line to both readers (`splitlines()` /
# `split(/\r?\n/)`), so the offset scan in `_portable` has to agree. It once did not:
# `_line_end` returned None at EOF, which made `split_frontmatter` report "no region to
# rewrite" for a document ending exactly at its closing fence — `--repair` silently
# skipped an artifact it could fix — and made `opens_frontmatter_fence` call a lone
# `---` fenceless.


def test_opens_frontmatter_fence_agrees_with_the_reader_at_eof() -> None:
    from softschema._portable import opens_frontmatter_fence

    # No trailing newline. The reader treats this as an opened, unterminated fence, so
    # detection must too, or the two disagree about what the document even is.
    assert opens_frontmatter_fence("---") is True
    assert opens_frontmatter_fence("---\n") is True
    assert opens_frontmatter_fence("") is False
    assert opens_frontmatter_fence("name: Acme") is False


def test_split_frontmatter_finds_a_region_ending_at_the_closing_fence() -> None:
    from softschema._portable import split_frontmatter

    # The closing fence is the last thing in the file, with no trailing newline — a very
    # ordinary shape for agent-written text, and one `--repair` must not skip.
    ended_at_fence = split_frontmatter("---\nname: Acme\n---")
    assert ended_at_fence is not None
    assert ended_at_fence.metadata_text == "name: Acme\n"
    # An empty body, and the file's missing trailing newline preserved by the offsets.
    assert ended_at_fence.body_offset == len("---\nname: Acme\n---")

    # Unchanged: a fence that never closes still has no region to rewrite.
    assert split_frontmatter("---\nname: Acme") is None


def test_repair_fixes_a_document_that_ends_at_its_closing_fence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Two documents differing only in a trailing newline must get the same verdict.
    # Before the fix the newline-less one was reported unreadable and left unrepaired.
    body = (
        "---\nsoftschema:\n  contract: test.detect:Doc/v1\n  schema: mini.schema.yaml\n"
        "  envelope: rec\nrec:\n  name: Note: actually Q1\n---"
    )
    for name, text in (("with-nl.md", body + "\n"), ("no-nl.md", body)):
        path = _detect_case(tmp_path, name, text)
        assert softschema_main(["repair", str(path), "--check"]) == 1
        result = json.loads(capsys.readouterr().out)
        assert result["outcome"] == "valid", name
        assert [r["code"] for r in result["repairs"]] == ["yaml_quoted_scalar"], name


# --- A leading byte order mark -------------------------------------------------------
#
# The BOM is invisible, legal, and written by ordinary tools, so it reaches softschema
# on real agent output. It once split the two runtimes: `TextDecoder`'s default strips
# it, `bytes.decode` kept it, and every fence comparison in the codebase asks whether a
# first line equals `---`. `"\ufeff---"` does not, so Python called the document
# fenceless and TypeScript read it — opposite verdicts on identical bytes.


def test_read_utf8_drops_a_leading_bom_and_keeps_every_other(tmp_path: Path) -> None:
    from softschema._portable import read_utf8

    path = tmp_path / "bom.md"
    path.write_bytes("\ufeff---\nname: Acme\n---\n".encode())
    assert read_utf8(path) == "---\nname: Acme\n---\n"

    # Only position zero. A U+FEFF anywhere else is a real character in a real value.
    path.write_bytes("---\nname: A\ufeffcme\n---\n".encode())
    assert read_utf8(path) == "---\nname: A\ufeffcme\n---\n"

    # A document with no mark is returned unchanged, not merely equal.
    path.write_bytes(b"name: Acme\n")
    assert read_utf8(path) == "name: Acme\n"


def test_a_bom_prefixed_artifact_is_read_not_called_fenceless(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The frontmatter is plainly there; reporting "no YAML frontmatter" would send an
    # agent after a block it can see, and asking for `--contract` would advise a flag
    # that cannot help.
    (tmp_path / "mini.schema.yaml").write_text(MINI_SCHEMA)
    path = tmp_path / "bom.md"
    path.write_bytes(f"\ufeff---\n{_FRONTMATTER_BODY}\n---\n# Acme\n".encode())

    assert softschema_main(["validate", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["values"] == {"name": "Acme"}

    assert softschema_main(["repair", str(path), "--check"]) == 0
    assert json.loads(capsys.readouterr().out)["outcome"] == "valid"


def test_a_bom_prefixed_artifact_repairs_like_the_same_file_without_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Two documents differing only by the mark must get the same verdict and the same
    # repair, the way the trailing-newline pair above must.
    body = (
        "---\nsoftschema:\n  contract: test.detect:Doc/v1\n  schema: mini.schema.yaml\n"
        "  envelope: rec\nrec:\n  name: Note: actually Q1\n---\n"
    )
    (tmp_path / "mini.schema.yaml").write_text(MINI_SCHEMA)
    for name, text in (("plain.md", body), ("bom.md", "\ufeff" + body)):
        path = tmp_path / name
        path.write_bytes(text.encode())
        assert softschema_main(["repair", str(path)]) == 0
        result = json.loads(capsys.readouterr().out)
        assert result["outcome"] == "valid", name
        assert [r["code"] for r in result["repairs"]] == ["yaml_quoted_scalar"], name
        # Rewriting drops the mark, so both files land on identical bytes. Repair only
        # writes when it has a change to make, so a clean BOM document keeps its mark.
        assert path.read_bytes() == (
            b"---\nsoftschema:\n  contract: test.detect:Doc/v1\n  schema: mini.schema.yaml\n"
            b'  envelope: rec\nrec:\n  name: "Note: actually Q1"\n---\n'
        ), name


def test_unparsable_frontmatter_names_the_parse_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Repair could not rescue it, and no binding flags were passed. The record must name
    # what actually went wrong instead of reporting a frontmatter block that is present.
    broken = "---\nsoftschema:\n  contract: test.detect:Doc/v1\nrec: [unclosed\n---\n# Body\n"
    path = _detect_case(tmp_path, "broken.md", broken)
    assert softschema_main(["repair", str(path), "--check"]) == 1
    record = json.loads(capsys.readouterr().out)["structural"]["errors"][0]
    assert "has no YAML frontmatter" not in record["message"]
    # The reader's own diagnosis, not a restatement that something went wrong.
    assert "flow sequence" in record["message"] or "expected" in record["message"]


# --- The `repair` command --------------------------------------------------------------
#
# `repair` is its own command because it answers a different question from `validate` and
# has the opposite posture toward an unreadable document. `validate` is the consuming-side
# gate and refuses one; `repair` is the producing-side loop and reports one. See
# docs/project/specs/active/plan-2026-08-30-repair-command.md.

_NEEDS_REPAIR = dedent(
    """
    ---
    softschema:
      contract: test.detect:Doc/v1
      schema: mini.schema.yaml
      envelope: rec
    rec:
      name: Note: actually Q1
    ---
    # Body
    """
).lstrip()

_UNREADABLE = "---\nsoftschema:\n  contract: test.detect:Doc/v1\n  envelope: rec\nrec:\n  name: A\n"


def test_repair_writes_but_dry_run_and_check_do_not(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for name, extra, expected_exit in (
        ("written.md", [], 0),
        ("dry.md", ["--dry-run"], 0),
        ("checked.md", ["--check"], 1),
    ):
        path = _detect_case(tmp_path, name, _NEEDS_REPAIR)
        before = path.read_bytes()
        assert softschema_main(["repair", str(path), *extra]) == expected_exit, name
        result = json.loads(capsys.readouterr().out)
        # Every mode reaches the same verdict and reports the same change; they differ
        # only in whether the file moves and what the exit code asserts.
        assert result["outcome"] == "valid", name
        assert [r["code"] for r in result["repairs"]] == ["yaml_quoted_scalar"], name
        assert (path.read_bytes() != before) is (extra == []), name


def test_repair_check_and_dry_run_differ_only_on_an_already_clean_document(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The whole reason both flags exist: --check asserts "nothing needed doing" and fails
    # a document that repairs cleanly, while --dry-run keeps the ordinary pass condition.
    clean = _NEEDS_REPAIR.replace("name: Note: actually Q1", 'name: "Note: actually Q1"')
    for name, text, dry_exit, check_exit in (
        ("dirty.md", _NEEDS_REPAIR, 0, 1),
        ("clean.md", clean, 0, 0),
    ):
        path = _detect_case(tmp_path, name, text)
        assert softschema_main(["repair", str(path), "--dry-run"]) == dry_exit, name
        capsys.readouterr()
        assert softschema_main(["repair", str(path), "--check"]) == check_exit, name
        capsys.readouterr()


def test_repair_dry_run_and_check_are_mutually_exclusive(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Checked by hand rather than with argparse's mutually exclusive group, so both CLIs
    # word softschema's own diagnostic identically. The group's message is argparse's and
    # Commander cannot reproduce it; the golden corpus asserts this line in full.
    path = _detect_case(tmp_path, "doc.md", _NEEDS_REPAIR)
    assert softschema_main(["repair", str(path), "--dry-run", "--check"]) == 2
    assert "--dry-run and --check are mutually exclusive" in capsys.readouterr().err


def test_validate_no_longer_accepts_the_retired_repair_flags(tmp_path: Path) -> None:
    path = _detect_case(tmp_path, "doc.md", _NEEDS_REPAIR)
    for flag in ("--repair", "--check-repair"):  # retired-surface-ok
        with pytest.raises(SystemExit) as excinfo:
            softschema_main(["validate", str(path), flag])
        assert excinfo.value.code == 2, flag


def test_validate_never_writes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _detect_case(tmp_path, "doc.md", _NEEDS_REPAIR)
    before = path.read_bytes()
    softschema_main(["validate", str(path)])
    capsys.readouterr()
    assert path.read_bytes() == before


# --- Strictness is a property of the command, not of which flags were passed ------------


def test_validate_refuses_an_unreadable_artifact_with_or_without_a_contract(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The leak this closes: `validate` read the document only when binding inference
    # needed it, so passing --contract removed the read and the same unreadable file
    # exited 1 with a record instead of 2 with a message. The verdict must not depend on
    # a flag that has nothing to do with whether the file can be opened.
    path = _detect_case(tmp_path, "unreadable.md", _UNREADABLE)
    for argv in (
        ["validate", str(path)],
        ["validate", str(path), "--contract", "test.detect:Doc/v1"],
    ):
        assert softschema_main(argv) == 2, argv
        captured = capsys.readouterr()
        assert captured.out == "", argv  # exit 2 is a message, never a result document
        assert "Delimiter `---` for end of frontmatter not found" in captured.err, argv


def test_repair_reports_an_unreadable_artifact_with_or_without_a_contract(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The mirror-image leak: `repair` is the checking posture by definition, but raised a
    # usage error about --contract when it could not infer a binding — advising a flag
    # that would not have helped, to the one caller who most needs the diagnostic.
    path = _detect_case(tmp_path, "unreadable.md", _UNREADABLE)
    for argv in (
        ["repair", str(path), "--check"],
        ["repair", str(path), "--check", "--contract", "test.detect:Doc/v1"],
    ):
        assert softschema_main(argv) == 1, argv
        captured = capsys.readouterr()
        assert captured.err == "", argv
        record = json.loads(captured.out)["structural"]["errors"][0]
        assert record["kind"] == "yaml_parse_error", argv
        assert "Delimiter `---` for end of frontmatter not found" in record["message"], argv
        assert "--contract" not in record["message"], argv


def test_repair_leaves_an_unreadable_artifact_untouched(tmp_path: Path) -> None:
    path = _detect_case(tmp_path, "unreadable.md", _UNREADABLE)
    before = path.read_bytes()
    assert softschema_main(["repair", str(path)]) == 1
    assert path.read_bytes() == before


# --- load_artifact: the strict consuming API -------------------------------------------


def test_load_artifact_returns_values_and_raises_on_anything_less(tmp_path: Path) -> None:
    from softschema import ArtifactInvalidError, Contract, SchemaProfile, load_artifact

    contract = Contract(
        id="test.detect:Doc/v1",
        profile=SchemaProfile.frontmatter_md,
        envelope_key="rec",
        schema_path=tmp_path / "mini.schema.yaml",
    )
    valid = _detect_case(tmp_path, "valid.md", f"---\n{_FRONTMATTER_BODY}\n---\n# Body\n")
    assert load_artifact(valid, contract=contract) == {"name": "Acme"}

    # The trap this closes: validate_artifact returns values=None here, so a consumer
    # that forgets to check `outcome` gets a TypeError naming neither the artifact nor
    # the reason.
    unreadable = _detect_case(tmp_path, "unreadable.md", _UNREADABLE)
    with pytest.raises(ArtifactInvalidError) as excinfo:
        load_artifact(unreadable, contract=contract)
    assert excinfo.value.result.outcome in {"invalid", "input_error"}
    assert "unreadable.md" in str(excinfo.value)
