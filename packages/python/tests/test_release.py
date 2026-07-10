"""Release metadata, immutable artifact, and workflow boundary tests."""

from __future__ import annotations

import hashlib
import json
import re
import tarfile
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
