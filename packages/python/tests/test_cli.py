from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest

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


def test_compile_writes_sidecar_and_exits_zero(
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


def test_compile_check_returns_one_when_sidecar_missing(tmp_path: Path, model_module: Path) -> None:
    out = tmp_path / "missing.schema.yaml"

    exit_code = softschema_main(["compile", SAMPLE_MODEL_SPEC, "--out", str(out), "--check"])

    assert exit_code == 1
    assert not out.exists()


def test_compile_check_returns_zero_when_sidecar_matches(
    tmp_path: Path, model_module: Path
) -> None:
    out = tmp_path / "sample.schema.yaml"
    softschema_main(["compile", SAMPLE_MODEL_SPEC, "--out", str(out)])

    exit_code = softschema_main(["compile", SAMPLE_MODEL_SPEC, "--out", str(out), "--check"])

    assert exit_code == 0


def test_compile_rejects_malformed_model_spec(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "sample.schema.yaml"

    exit_code = softschema_main(["compile", "bad-spec", "--out", str(out)])

    assert exit_code == 2
    assert "module:Class" in capsys.readouterr().err


def test_compile_rejects_non_basemodel(
    tmp_path: Path, model_module: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "sample.schema.yaml"

    exit_code = softschema_main(["compile", "test_cli_model:NotAModel", "--out", str(out)])

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
    assert "# Softschema Guide" in output
    assert "programming-language agnostic" in output
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
    assert "# Softschema Spec" in output["content"]


def test_skill_brief_points_agents_to_docs_and_rules(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = softschema_main(["skill", "--brief"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "softschema docs guide" in output
    assert "softschema docs spec" in output
    assert "Do not parse Markdown body prose or tables" in output


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


def test_validate_exits_two_when_validation_implementation_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
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
        """,
    )

    exit_code = softschema_main(["validate", str(doc)])

    assert exit_code == 2
    assert "--model" in capsys.readouterr().err


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
