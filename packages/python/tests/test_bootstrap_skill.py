"""Doctor-v1, deterministic bootstrap, and portable Agent Skill gates."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from skills_ref import read_properties
from skills_ref import validate as validate_skill

from softschema.cli import _brief_skill_text
from softschema.cli import main as softschema_main

ROOT = Path(__file__).resolve().parents[3]
CONFORMANCE = ROOT / "conformance"
SKILL = ROOT / "skills/softschema/SKILL.md"
MIRRORS = (
    ROOT / ".agents/skills/softschema/SKILL.md",
    ROOT / ".claude/skills/softschema/SKILL.md",
)
RELEASE_METADATA = ROOT / "release-metadata.json"
BUILD_METADATA = ROOT / "build-metadata.json"
PUBLIC_BOOTSTRAP_DOCS = (
    ROOT / "README.md",
    ROOT / "docs/installation.md",
    ROOT / "docs/softschema-guide.md",
    ROOT / "docs/e2e-testing.runbook.md",
    ROOT / "docs/publishing.md",
    ROOT / "packages/python/README.md",
    ROOT / "packages/typescript/README.md",
    ROOT / "SUPPLY-CHAIN-SECURITY.md",
    SKILL,
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _doctor_report(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    assert softschema_main(["doctor", "--json"]) == 0
    return json.loads(capsys.readouterr().out)


def _normalized_doctor(report: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(report))
    normalized["build"] = "<build-metadata>"
    normalized["package"]["version"] = "<logical-version>"
    normalized["package"]["release_state"] = "<release-state>"
    normalized["protocol_version"] = "<discovery-protocol>"
    normalized["runtime"] = {
        "name": "<runtime-name>",
        "version": "<runtime-version>",
    }
    normalized["capabilities"]["artifact_formats"] = ["<artifact-formats>"]
    normalized["capabilities"]["model_loaders"] = ["<model-loaders>"]
    normalized["capabilities"]["conformance"] = {
        "version": "<conformance-version>",
        "status": "<conformance-status>",
    }
    return normalized


def test_doctor_json_matches_shared_v1_golden_and_schema(
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = _doctor_report(capsys)
    release = _load_json(RELEASE_METADATA)
    build = _load_json(BUILD_METADATA)
    expected = _load_json(CONFORMANCE / "doctor/doctor-v1-common.golden.json")

    assert _normalized_doctor(report) == expected
    assert report["protocol_version"] == release["discovery_protocol"]
    assert report["package"] == {
        "name": "softschema",
        "version": release["logical_version"],
        "release_state": release["release_state"],
    }
    assert report["runtime"]["name"] == "python"
    assert release["artifact_formats"] == {
        "current": "1",
        "supported": ["legacy-0.2", "1"],
    }
    assert report["capabilities"]["artifact_formats"] == sorted(
        release["artifact_formats"]["supported"]
    )
    assert report["capabilities"]["model_loaders"] == ["json-schema", "pydantic"]
    assert report["capabilities"]["conformance"] == release["conformance"]
    assert report["build"] == build

    doctor_schema = _load_json(CONFORMANCE / "schemas/doctor-result.schema.json")
    build_schema = _load_json(CONFORMANCE / "schemas/build-metadata.schema.json")
    registry: Registry[Any] = Registry().with_resource(
        build_schema["$id"], Resource.from_contents(build_schema)
    )
    Draft202012Validator(doctor_schema, registry=registry).validate(report)


def test_bootstrap_commands_are_release_pinned_ordered_and_executable(
    tmp_path: Path,
) -> None:
    fixture = _load_json(CONFORMANCE / "agent-skills/bootstrap-commands-v1.json")
    release = _load_json(RELEASE_METADATA)
    commands = fixture["commands"]
    assert [item["kind"] for item in commands] == [
        "local",
        "python-fallback",
        "node-fallback",
        "bun-fallback",
    ]
    assert commands[1]["argv"][1] == f"softschema=={release['packages']['python']['pin']}"
    assert commands[2]["argv"][1] == f"softschema@{release['packages']['npm']['pin']}"
    assert commands[3]["argv"][1] == f"softschema@{release['packages']['npm']['pin']}"

    skill = SKILL.read_text(encoding="utf-8")
    brief = _brief_skill_text()
    offsets = [skill.index(item["command"]) for item in commands]
    assert offsets == sorted(offsets)
    assert all(item["command"] in brief for item in commands)

    if os.name == "nt":
        pytest.skip("POSIX executable-stub smoke")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "argv.log"
    for executable in ("softschema", "uvx", "npx", "bunx"):
        stub = bin_dir / executable
        stub.write_text(
            "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$BOOTSTRAP_LOG\"\nprintf '{}\\n'\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
    env = {**os.environ, "PATH": str(bin_dir), "BOOTSTRAP_LOG": str(log)}
    for item in commands:
        result = subprocess.run(
            shlex.split(item["command"]),
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout == "{}\n"
    assert log.read_text(encoding="utf-8").splitlines() == [
        " ".join(item["argv"]) for item in commands
    ]


def test_skill_is_officially_valid_concise_and_self_contained() -> None:
    for skill_dir in (SKILL.parent, *(mirror.parent for mirror in MIRRORS)):
        assert validate_skill(skill_dir) == []
    properties = read_properties(SKILL.parent)
    assert properties.name == SKILL.parent.name == "softschema"
    assert len(properties.description) <= 1024
    assert properties.allowed_tools is None
    assert properties.compatibility is None
    assert properties.license is None
    assert properties.metadata is None
    for cue in ("Markdown", "YAML", "frontmatter", "agent", "softschema"):
        assert cue.lower() in properties.description.lower()

    source = SKILL.read_text(encoding="utf-8")
    for path in (SKILL, *MIRRORS):
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 100
    assert "allowed-tools" not in source
    assert "$SS" not in source
    assert "@latest" not in source
    assert "npx --yes" in source
    brief = _brief_skill_text()
    assert "$SS" not in brief
    assert "@latest" not in brief
    assert "softschema doctor --json" in brief
    assert "softschema validate doc.md" in brief


def test_activation_matrix_covers_major_agents_and_positive_negative_prompts() -> None:
    matrix = _load_json(CONFORMANCE / "agent-skills/activation-matrix-v1.json")
    assert matrix["version"] == "activation-matrix-v1"
    assert {item["agent"] for item in matrix["observations"]} == {
        "codex",
        "claude",
        "gemini",
        "copilot",
        "cursor",
        "windsurf",
        "opencode",
        "aider",
        "cline",
        "roo",
    }
    assert {item["expected_activation"] for item in matrix["activation_cases"]} == {
        True,
        False,
    }
    required = {"agent", "surface", "model", "version", "date", "prompt", "observed_result"}
    assert all(required <= item.keys() for item in matrix["observations"])
    assert not any(item["activation_observed"] for item in matrix["observations"])


def test_public_bootstrap_docs_have_no_unpinned_latest_claims() -> None:
    for path in PUBLIC_BOOTSTRAP_DOCS:
        text = path.read_text(encoding="utf-8")
        assert "@latest" not in text, path
    release = _load_json(RELEASE_METADATA)
    python_pin = release["packages"]["python"]["pin"]
    npm_pin = release["packages"]["npm"]["pin"]
    for path in (
        ROOT / "README.md",
        ROOT / "docs/e2e-testing.runbook.md",
        ROOT / "docs/installation.md",
        ROOT / "docs/softschema-guide.md",
        SKILL,
    ):
        text = path.read_text(encoding="utf-8")
        assert f"softschema=={python_pin}" in text, path
        assert f"softschema@{npm_pin}" in text, path

    package_versions = release["packages"]
    assert f"softschema=={package_versions['python']['version']}" in (
        ROOT / "packages/python/README.md"
    ).read_text(encoding="utf-8")
    assert f"softschema@{package_versions['npm']['version']}" in (
        ROOT / "packages/typescript/README.md"
    ).read_text(encoding="utf-8")
