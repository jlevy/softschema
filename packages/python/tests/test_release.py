"""Release metadata, immutable artifact, and workflow boundary tests."""

from __future__ import annotations

import hashlib
import json
import re
import tarfile
import tomllib
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from devtools.release import (
    ReleaseError,
    ReleaseSubject,
    SubjectKind,
    build_conformance_archive,
    build_metadata,
    build_release_manifest,
    load_and_validate_metadata,
    release_coordinates,
    verify_release_manifest,
)
from devtools.verify_installed_wheel import WheelVerificationError, _safe_wheel_path

ROOT = Path(__file__).parents[3]
FULL_SHA = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _workflow(path: str) -> dict[str, Any]:
    value = YAML(typ="safe").load(ROOT / path)
    assert isinstance(value, dict)
    return value


@pytest.mark.parametrize(
    ("tag", "logical", "python_version", "npm_version", "npm_tag", "prerelease"),
    [
        ("v0.3.0", "0.3.0", "0.3.0", "0.3.0", "latest", False),
        ("v0.3.0-rc.2", "0.3.0-rc.2", "0.3.0rc2", "0.3.0-rc.2", "next", True),
    ],
)
def test_release_tag_mapping_is_ecosystem_specific(
    tag: str,
    logical: str,
    python_version: str,
    npm_version: str,
    npm_tag: str,
    prerelease: bool,
) -> None:
    coordinates = release_coordinates(tag)
    assert coordinates.logical_version == logical
    assert coordinates.python_version == python_version
    assert coordinates.npm_version == npm_version
    assert coordinates.npm_tag == npm_tag
    assert coordinates.prerelease is prerelease


@pytest.mark.parametrize("tag", ["0.3.0", "v0.3", "v0.3.0-beta.1", "v0.3.0-rc", "v01.2.3"])
def test_release_tag_mapping_rejects_every_other_shape(tag: str) -> None:
    with pytest.raises(ReleaseError):
        release_coordinates(tag)


def test_root_release_and_development_build_metadata_validate() -> None:
    metadata = load_and_validate_metadata(ROOT)
    assert metadata["release_state"] == "development"
    assert metadata["packages"]["python"]["pin"] == "0.2.2"
    assert metadata["packages"]["npm"]["pin"] == "0.2.2"

    build = json.loads((ROOT / "build-metadata.json").read_text(encoding="utf-8"))
    assert build["release_metadata_sha256"] == _sha256(ROOT / "release-metadata.json")
    assert (
        build_metadata(
            ROOT,
            source_commit="0" * 40,
            conformance_archive=None,
        )
        == build
    )


def test_release_metadata_parser_rejects_duplicate_keys(tmp_path: Path) -> None:
    original = (ROOT / "release-metadata.json").read_text(encoding="utf-8").rstrip()
    duplicate = original[:-1] + ',\n  "schema_version": "1"\n}\n'
    (tmp_path / "release-metadata.json").write_text(duplicate, encoding="utf-8")
    with pytest.raises(ReleaseError, match="duplicate JSON key"):
        load_and_validate_metadata(tmp_path)


def test_conformance_archive_is_deterministic_and_contains_only_relative_files(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    build_conformance_archive(ROOT, first)
    build_conformance_archive(ROOT, second)
    assert first.read_bytes() == second.read_bytes()

    with tarfile.open(first, "r:gz") as archive:
        names = archive.getnames()
        assert names == sorted(names)
        assert names
        assert all(not name.startswith(("/", "../")) for name in names)
        assert "conformance/manifest.yaml" in names
        assert not any(name.startswith("conformance/skill-installer/") for name in names)


def test_build_metadata_is_source_derived_and_non_self_referential(tmp_path: Path) -> None:
    archive = tmp_path / "conformance.tar.gz"
    build_conformance_archive(ROOT, archive)
    metadata = build_metadata(ROOT, source_commit="a" * 40, conformance_archive=archive)
    assert metadata["source_commit"] == "a" * 40
    assert metadata["conformance_sha256"] == _sha256(archive)
    assert metadata["build_id"].startswith("sha256:")
    assert "package_sha256" not in metadata


def test_release_manifest_owns_exact_primary_subject_digests(tmp_path: Path) -> None:
    files: list[ReleaseSubject] = []
    subjects: list[tuple[SubjectKind, str, bytes]] = [
        ("wheel", "softschema-0.2.2-py3-none-any.whl", b"wheel"),
        ("sdist", "softschema-0.2.2.tar.gz", b"sdist"),
        ("npm", "softschema-0.2.2.tgz", b"npm"),
        ("release_metadata", "release-metadata.json", b"{}"),
        ("build_metadata", "build-metadata.json", b"{}"),
    ]
    for kind, name, content in subjects:
        path = tmp_path / name
        path.write_bytes(content)
        files.append(ReleaseSubject(kind=kind, path=path))

    manifest = build_release_manifest(
        logical_version="0.2.2",
        source_commit="b" * 40,
        subjects=files,
    )
    assert set(manifest["subjects"]) == {subject.path.name for subject in files}
    assert "release-manifest.json" not in manifest["subjects"]
    for subject in files:
        assert manifest["subjects"][subject.path.name]["sha256"] == _sha256(subject.path)
    verify_release_manifest(manifest, tmp_path)

    extra = tmp_path / "unreviewed.tgz"
    extra.write_bytes(b"extra")
    with pytest.raises(ReleaseError, match="inventory mismatch"):
        verify_release_manifest(manifest, tmp_path)
    extra.unlink()

    (tmp_path / files[0].path.name).write_bytes(b"changed")
    with pytest.raises(ReleaseError, match="digest mismatch"):
        verify_release_manifest(manifest, tmp_path)


def test_release_manifest_rejects_unsafe_or_duplicate_subject_names(tmp_path: Path) -> None:
    safe = tmp_path / "artifact.whl"
    safe.write_bytes(b"safe")
    with pytest.raises(ReleaseError):
        build_release_manifest(
            logical_version="0.2.2",
            source_commit="c" * 40,
            subjects=[
                ReleaseSubject(kind="wheel", path=safe),
                ReleaseSubject(kind="sdist", path=safe),
            ],
        )

    empty = tmp_path / "empty.whl"
    empty.touch()
    with pytest.raises(ReleaseError, match="validation failed"):
        build_release_manifest(
            logical_version="0.2.2",
            source_commit="c" * 40,
            subjects=[ReleaseSubject(kind="wheel", path=empty)],
        )

    symlink = tmp_path / "linked.whl"
    symlink.symlink_to(safe)
    with pytest.raises(ReleaseError, match="regular file"):
        build_release_manifest(
            logical_version="0.2.2",
            source_commit="c" * 40,
            subjects=[ReleaseSubject(kind="wheel", path=symlink)],
        )


def test_both_packages_embed_release_and_build_metadata() -> None:
    import tomllib

    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force_include["release-metadata.json"] == "softschema/resources/release-metadata.json"
    assert force_include["build-metadata.json"] == "softschema/resources/build-metadata.json"

    resources = (ROOT / "packages/typescript/src/resources-manifest.ts").read_text(encoding="utf-8")
    assert '"release-metadata.json"' in resources
    assert '"build-metadata.json"' in resources


def test_every_github_action_is_pinned_and_publishers_do_not_checkout_source() -> None:
    for workflow_path in [".github/workflows/ci.yml", ".github/workflows/publish.yml"]:
        workflow = _workflow(workflow_path)
        for job_name, job in workflow["jobs"].items():
            for step in job.get("steps", []):
                action = step.get("uses")
                if action is not None:
                    assert FULL_SHA.fullmatch(action), f"{workflow_path}/{job_name}: {action}"

    publish = _workflow(".github/workflows/publish.yml")
    assert publish["permissions"] == {}
    for job_name in ["publish-pypi", "publish-npm"]:
        job = publish["jobs"][job_name]
        assert job["permissions"] == {"id-token": "write"}
        assert job["environment"] in {"pypi", "npm"}
        actions = [step.get("uses", "") for step in job["steps"]]
        assert not any(action.startswith("actions/checkout@") for action in actions)
        assert job["needs"] == ["preflight", "smoke"]
        scripts = "\n".join(step.get("run", "") for step in job["steps"])
        assert not any(
            forbidden in scripts
            for forbidden in ["uv sync", "npm install", "bun install", "pytest", "bun run"]
        )


def test_build_constraints_pin_versions_and_hash_every_requirement() -> None:
    text = (ROOT / "build-constraints.txt").read_text(encoding="utf-8")
    requirement_lines = [line for line in text.splitlines() if line and not line[0].isspace()]
    requirement_lines = [line for line in requirement_lines if not line.startswith("#")]
    assert requirement_lines
    assert all(re.fullmatch(r"[a-z0-9-]+==[^ ]+ \\", line) for line in requirement_lines)
    assert text.count("--hash=sha256:") >= len(requirement_lines)


def test_publish_workflow_is_tag_protected_and_manual_runs_are_dry_only() -> None:
    publish = _workflow(".github/workflows/publish.yml")
    assert publish["concurrency"]["cancel-in-progress"] is False
    assert publish["on"]["push"]["tags"] == ["v*.*.*"]
    assert "workflow_dispatch" in publish["on"]
    preflight_script = "\n".join(
        step.get("run", "") for step in publish["jobs"]["preflight"]["steps"]
    )
    assert "github.ref_protected" in preflight_script
    assert "git rev-parse 'HEAD^{commit}'" in preflight_script
    assert "--clear --out-dir release-out" not in preflight_script
    assert "--no-create-gitignore --out-dir python-dist" in preflight_script
    assert "sha256sum --check SHA256SUMS" in "\n".join(
        step.get("run", "")
        for name in ["smoke", "publish-pypi", "publish-npm"]
        for step in publish["jobs"][name]["steps"]
    )
    for job_name in ["publish-pypi", "publish-npm"]:
        assert "github.event_name == 'push'" in publish["jobs"][job_name]["if"]


def test_ci_installs_and_verifies_local_wheels_while_forbidding_dependency_builds() -> None:
    ci = _workflow(".github/workflows/ci.yml")
    for job_name in ["build", "golden", "cross-impl"]:
        steps = ci["jobs"][job_name]["steps"]
        build_index, build_step = next(
            (index, step) for index, step in enumerate(steps) if "uv build" in step.get("run", "")
        )
        install_index, install_step = next(
            (index, step)
            for index, step in enumerate(steps)
            if "without builds" in step.get("name", "").lower()
        )
        assert build_index < install_index
        assert "--build-constraint build-constraints.txt" in build_step["run"]
        assert "--require-hashes" in build_step["run"]
        assert install_step["env"] == {"UV_NO_BUILD": "1"}
        install_script = install_step["run"]
        assert "uv sync --all-extras --frozen --no-cache --no-install-project" in install_script
        assert "uv pip install --no-build --no-deps" in install_script
        assert "devtools/verify_installed_wheel.py" in install_script
        assert "--editable" not in "\n".join(step.get("run", "") for step in steps)

    candidate = ci["jobs"]["artifact-candidate"]
    candidate_scripts = "\n".join(step.get("run", "") for step in candidate["steps"])
    assert "frozen_artifact_smoke.py build artifact-out" in candidate_scripts
    assert 'test "$(npm --version)" = "11.16.0"' in candidate_scripts
    assert (
        sum(
            step.get("uses", "").startswith("actions/upload-artifact@")
            for step in candidate["steps"]
        )
        == 1
    )

    artifact_smoke = ci["jobs"]["artifact-smoke"]
    assert artifact_smoke["needs"] == "artifact-candidate"
    actions = [step.get("uses", "") for step in artifact_smoke["steps"]]
    assert sum(action.startswith("actions/download-artifact@") for action in actions) == 1
    assert not any(action.startswith("actions/checkout@") for action in actions)
    checksum_index = next(
        index
        for index, step in enumerate(artifact_smoke["steps"])
        if step.get("name") == "Verify candidate checksums before any candidate install"
    )
    smoke_index = next(
        index
        for index, step in enumerate(artifact_smoke["steps"])
        if step.get("name") == "Inspect, install, and execute the exact candidate"
    )
    assert checksum_index < smoke_index
    smoke_scripts = "\n".join(step.get("run", "") for step in artifact_smoke["steps"])
    assert "frozen_artifact_smoke.py verify-checksums artifact-out" in smoke_scripts
    assert "frozen_artifact_smoke.py smoke artifact-out" in smoke_scripts
    assert not any(
        forbidden in smoke_scripts
        for forbidden in [
            "uv sync",
            "uv build",
            "uv pip install",
            "bun install",
            "bun run",
            "npm install",
            "npm pack",
            "pytest",
            "--editable",
        ]
    )


def test_publish_forbids_dependency_builds_without_prebuilding_the_candidate() -> None:
    publish = _workflow(".github/workflows/publish.yml")
    steps = publish["jobs"]["preflight"]["steps"]
    dependency_index, dependency_step = next(
        (index, step)
        for index, step in enumerate(steps)
        if step.get("name") == "Install frozen Python dependencies without builds"
    )
    editable_index, editable_step = next(
        (index, step)
        for index, step in enumerate(steps)
        if step.get("name") == "Install the trusted checkout for preflight"
    )
    audit_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Audit the frozen Python dependency environment"
    )
    metadata_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Derive build metadata before either package build"
    )
    candidate_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Build Python artifacts once with hash-locked build dependencies"
    )
    assert dependency_index < audit_index < editable_index < metadata_index < candidate_index
    assert dependency_step["env"] == {"UV_NO_BUILD": "1"}
    assert dependency_step["run"].endswith("--no-cache --no-install-project")
    assert "env" not in editable_step
    assert editable_step["run"] == "uv pip install --no-build-isolation --no-deps --editable ."
    scripts = "\n".join(step.get("run", "") for step in steps)
    assert "npm_consumer.py create release-out/npm-consumer" in scripts
    assert "frozen_artifact_smoke.py stage release-out" in scripts
    smoke_scripts = "\n".join(step.get("run", "") for step in publish["jobs"]["smoke"]["steps"])
    assert "frozen_artifact_smoke.py verify-checksums release-out" in smoke_scripts
    assert "frozen_artifact_smoke.py smoke release-out" in smoke_scripts


def test_locked_dependency_audits_fail_without_downgrade() -> None:
    ci = _workflow(".github/workflows/ci.yml")
    audit = ci["jobs"]["dependency-audit"]
    scripts = "\n".join(step.get("run", "") for step in audit["steps"])
    assert "uv sync --all-extras --group audit --frozen --no-cache --no-install-project" in scripts
    assert "uv run --no-sync pip-audit --local --strict --progress-spinner=off" in scripts
    assert "bun install --frozen-lockfile --ignore-scripts" in scripts
    assert "bun audit --audit-level=moderate" in scripts
    assert "|| true" not in scripts
    assert not audit.get("continue-on-error", False)
    assert not any(step.get("continue-on-error", False) for step in audit["steps"])
    for job_name in ["build", "golden", "cross-impl", "artifact-candidate"]:
        ordinary_scripts = "\n".join(step.get("run", "") for step in ci["jobs"][job_name]["steps"])
        assert "--group audit" not in ordinary_scripts

    publish = _workflow(".github/workflows/publish.yml")
    preflight = "\n".join(step.get("run", "") for step in publish["jobs"]["preflight"]["steps"])
    assert "uv sync --all-extras --group audit --frozen" in preflight
    assert "pip-audit --local --strict --progress-spinner=off" in preflight
    assert "bun audit --audit-level=moderate" in preflight
    assert "npm_consumer.py create release-out/npm-consumer" in preflight
    assert "|| true" not in preflight


def test_runtime_dependencies_have_compatible_bounds_and_audit_tool_is_frozen() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert set(project["project"]["dependencies"]) == {
        "frontmatter-format>=0.3.0,<0.4",
        "jsonschema>=4.20,<5",
        "pydantic>=2,<3",
        "ruamel-yaml>=0.18,<0.20",
        "strif>=3.1.0,<4",
    }
    assert set(project["dependency-groups"]["audit"]) == {
        "msgpack==1.2.1",
        "pip-audit==2.10.0",
    }

    npm = json.loads((ROOT / "packages/typescript/package.json").read_text(encoding="utf-8"))
    assert npm["dependencies"]
    assert all(
        re.fullmatch(r"\^[0-9]+\.[0-9]+\.[0-9]+", value) for value in npm["dependencies"].values()
    )
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    audit_package = next(item for item in lock["package"] if item["name"] == "pip-audit")
    assert audit_package["version"] == "2.10.0"
    yaml_package = next(item for item in lock["package"] if item["name"] == "ruamel-yaml")
    assert yaml_package["version"] == "0.19.1"


def test_all_workflows_pin_the_audited_uv_release() -> None:
    for workflow_path in [".github/workflows/ci.yml", ".github/workflows/publish.yml"]:
        workflow = _workflow(workflow_path)
        uv_steps = [
            step
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            if step.get("uses", "").startswith("astral-sh/setup-uv@")
        ]
        assert uv_steps
        assert all(step["with"]["version"] == "0.11.21" for step in uv_steps)


def test_skills_reference_validator_is_a_hash_locked_wheel_dependency() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "skills-ref==0.1.1" in project["dependency-groups"]["dev"]

    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    assert lock["options"] == {
        "exclude-newer": "2026-06-20T00:00:00Z",
        "exclude-newer-package": {"strif": "2026-06-03T00:00:00Z"},
    }
    package = next(item for item in lock["package"] if item["name"] == "skills-ref")
    assert package["version"] == "0.1.1"
    assert package["source"] == {"registry": "https://pypi.org/simple"}
    assert package["wheels"] == [
        {
            "url": "https://files.pythonhosted.org/packages/af/25/"
            "36a43c3a61fb6cc3984e6ad5e556929b8ae71c95eba615dae4cf2f427964/"
            "skills_ref-0.1.1-py3-none-any.whl",
            "hash": "sha256:d35db5bb8de71ae301daf5ca9cb71f8a555e8c6f83a6d40e46a5bc09f8f461b5",
            "size": 12918,
            "upload-time": "2026-01-10T13:23:40.106Z",
        }
    ]


@pytest.mark.parametrize(
    "path",
    ["", ".", "../escape", "a/../escape", "a//escape", r"..\escape", "C:/escape"],
)
def test_wheel_verifier_rejects_ambiguous_or_traversing_record_paths(path: str) -> None:
    with pytest.raises(WheelVerificationError, match="unsafe path"):
        _safe_wheel_path(path)
