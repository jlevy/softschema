"""Tests for the frozen npm artifact-consumer boundary."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from devtools import npm_consumer


def _write_tarball(path: Path) -> None:
    package = {
        "name": "softschema",
        "version": "0.3.0",
        "dependencies": {"ajv": "^8.17.1"},
    }
    payload = (json.dumps(package, sort_keys=True) + "\n").encode()
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo("package/package.json")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))


def _integrity(path: Path) -> str:
    digest = base64.b64encode(hashlib.sha512(path.read_bytes()).digest()).decode("ascii")
    return f"sha512-{digest}"


def _registry_integrity() -> str:
    digest = base64.b64encode(hashlib.sha512(b"registry package").digest()).decode("ascii")
    return f"sha512-{digest}"


def _lock(tarball: Path) -> dict[str, Any]:
    spec = f"file:../{tarball.name}"
    return {
        "name": "softschema-artifact-consumer",
        "version": "0.0.0",
        "lockfileVersion": 3,
        "requires": True,
        "packages": {
            "": {
                "name": "softschema-artifact-consumer",
                "version": "0.0.0",
                "dependencies": {"softschema": spec},
            },
            "node_modules/ajv": {
                "version": "8.17.1",
                "resolved": "https://registry.npmjs.org/ajv/-/ajv-8.17.1.tgz",
                "integrity": _registry_integrity(),
            },
            "node_modules/softschema": {
                "version": "0.3.0",
                "resolved": spec,
                "integrity": _integrity(tarball),
                "dependencies": {"ajv": "^8.17.1"},
            },
        },
    }


def _fake_npm(monkeypatch: pytest.MonkeyPatch, tarball: Path) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(arguments: list[str], *, cwd: Path) -> str:
        calls.append(arguments)
        if arguments == ["npm", "--version"]:
            return "11.16.0\n"
        if arguments[:2] == ["npm", "install"]:
            (cwd / "package-lock.json").write_text(
                json.dumps(_lock(tarball), indent=2) + "\n",
                encoding="utf-8",
            )
            return ""
        if arguments[:2] in (["npm", "audit"], ["npm", "ci"]):
            if arguments[1] == "ci":
                package = cwd / "node_modules" / "softschema"
                package.mkdir(parents=True)
                (package / "package.json").write_text(
                    '{"name":"softschema","version":"0.3.0"}\n',
                    encoding="utf-8",
                )
            return ""
        raise AssertionError(arguments)

    monkeypatch.setattr(npm_consumer, "_run_npm", run)
    return calls


def test_create_records_and_verifies_the_frozen_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tarball = tmp_path / "softschema-0.3.0.tgz"
    _write_tarball(tarball)
    calls = _fake_npm(monkeypatch, tarball)
    bundle = tmp_path / "npm-consumer"

    npm_consumer.create_consumer_bundle(
        bundle,
        tarball,
        cutoff="2026-06-20T00:00:00Z",
        expected_npm_version="11.16.0",
        now=datetime(2026, 7, 10, tzinfo=UTC),
    )

    control = npm_consumer.verify_consumer_bundle(bundle, tarball)
    assert control["resolution"] == {
        "cutoff": "2026-06-20T00:00:00Z",
        "minimum_release_age_days": 14,
        "npm_version": "11.16.0",
        "registry": "https://registry.npmjs.org/",
        "flags": npm_consumer.RESOLUTION_FLAGS,
        "configuration": {
            "ambient_npm_environment": "removed",
            "user_config": "empty_ephemeral",
            "global_config": "empty_ephemeral",
            "project_config": "absent_from_owned_bundle",
        },
    }
    assert control["audit"]["failure_policy"] == "fail_on_moderate_or_higher"
    assert calls[1][:3] == ["npm", "install", "--package-lock-only"]
    assert "--before=2026-06-20T00:00:00Z" in calls[1]
    assert calls[2][:3] == ["npm", "audit", "--package-lock-only"]
    assert "--audit-level=moderate" in calls[2]


def test_create_requires_the_pinned_npm_and_full_cool_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tarball = tmp_path / "softschema-0.3.0.tgz"
    _write_tarball(tarball)
    calls = _fake_npm(monkeypatch, tarball)

    with pytest.raises(npm_consumer.NpmConsumerError, match="at least 14 days"):
        npm_consumer.create_consumer_bundle(
            tmp_path / "too-new",
            tarball,
            cutoff="2026-07-01T00:00:00Z",
            expected_npm_version="11.16.0",
            now=datetime(2026, 7, 10, tzinfo=UTC),
        )
    assert calls == []

    monkeypatch.setattr(npm_consumer, "_run_npm", lambda _arguments, *, cwd: "11.15.0\n")
    with pytest.raises(npm_consumer.NpmConsumerError, match=r"expected npm 11\.16\.0"):
        npm_consumer.create_consumer_bundle(
            tmp_path / "wrong-npm",
            tarball,
            cutoff="2026-06-20T00:00:00Z",
            expected_npm_version="11.16.0",
            now=datetime(2026, 7, 10, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "second_local",
        "missing_integrity",
        "wrong_sri",
        "traversing_path",
        "explicit_registry_port",
    ],
)
def test_lock_verifier_rejects_unfrozen_or_unowned_entries(tmp_path: Path, mutation: str) -> None:
    tarball = tmp_path / "softschema-0.3.0.tgz"
    _write_tarball(tarball)
    lock = _lock(tarball)
    if mutation == "second_local":
        lock["packages"]["node_modules/other"] = {
            "version": "1.0.0",
            "resolved": "file:../other.tgz",
            "integrity": "sha512-b3RoZXI=",
        }
    elif mutation == "missing_integrity":
        del lock["packages"]["node_modules/ajv"]["integrity"]
    elif mutation == "wrong_sri":
        lock["packages"]["node_modules/softschema"]["integrity"] = "sha512-d3Jvbmc="
    elif mutation == "traversing_path":
        lock["packages"]["node_modules/ajv/../escape"] = lock["packages"].pop("node_modules/ajv")
    else:
        lock["packages"]["node_modules/ajv"]["resolved"] = (
            "https://registry.npmjs.org:443/ajv/-/ajv-8.17.1.tgz"
        )

    with pytest.raises(npm_consumer.NpmConsumerError):
        npm_consumer.validate_package_lock(lock, tarball)


def test_bundle_control_owns_every_input_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tarball = tmp_path / "softschema-0.3.0.tgz"
    _write_tarball(tarball)
    _fake_npm(monkeypatch, tarball)
    bundle = tmp_path / "npm-consumer"
    npm_consumer.create_consumer_bundle(
        bundle,
        tarball,
        cutoff="2026-06-20T00:00:00Z",
        expected_npm_version="11.16.0",
        now=datetime(2026, 7, 10, tzinfo=UTC),
    )

    package = bundle / "package.json"
    package.write_text(package.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(npm_consumer.NpmConsumerError, match=r"package\.json digest"):
        npm_consumer.verify_consumer_bundle(bundle, tarball)


def test_bundle_verification_rechecks_cutoff_and_rejects_symlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tarball = tmp_path / "softschema-0.3.0.tgz"
    _write_tarball(tarball)
    _fake_npm(monkeypatch, tarball)
    bundle = tmp_path / "bundle"
    npm_consumer.create_consumer_bundle(
        bundle,
        tarball,
        cutoff="2026-06-20T00:00:00Z",
        expected_npm_version="11.16.0",
        now=datetime(2026, 7, 10, tzinfo=UTC),
    )

    with pytest.raises(npm_consumer.NpmConsumerError, match="at least 14 days"):
        npm_consumer.verify_consumer_bundle(
            bundle,
            tarball,
            now=datetime(2026, 6, 25, tzinfo=UTC),
        )

    linked_bundle = tmp_path / "linked-bundle"
    linked_bundle.symlink_to(bundle, target_is_directory=True)
    with pytest.raises(npm_consumer.NpmConsumerError, match="must be a directory"):
        npm_consumer.verify_consumer_bundle(linked_bundle, tarball)

    linked_tarball = tmp_path / "linked.tgz"
    linked_tarball.symlink_to(tarball)
    with pytest.raises(npm_consumer.NpmConsumerError, match="regular file"):
        npm_consumer.verify_consumer_bundle(bundle, linked_tarball)


def test_install_uses_npm_ci_without_mutating_the_frozen_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tarball = tmp_path / "softschema-0.3.0.tgz"
    _write_tarball(tarball)
    calls = _fake_npm(monkeypatch, tarball)
    bundle = tmp_path / "bundle"
    npm_consumer.create_consumer_bundle(
        bundle,
        tarball,
        cutoff="2026-06-20T00:00:00Z",
        expected_npm_version="11.16.0",
        now=datetime(2026, 7, 10, tzinfo=UTC),
    )

    destination = tmp_path / "isolated" / "npm-consumer"
    npm_consumer.install_consumer_bundle(bundle, tarball, destination)

    assert calls[-1] == ["npm", *npm_consumer.CI_FLAGS]
    assert json.loads((destination / "package-lock.json").read_text())["lockfileVersion"] == 3


def test_npm_environment_drops_ambient_npm_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NPM_CONFIG_REGISTRY", "https://attacker.invalid/")
    monkeypatch.setenv("npm_config_cache", "/tmp/ambient-cache")
    monkeypatch.setenv("NODE_AUTH_TOKEN", "must-not-leak")
    environment = npm_consumer._npm_environment(
        user_config=Path("/empty/user.npmrc"),
        global_config=Path("/empty/global.npmrc"),
    )
    assert environment["NPM_CONFIG_USERCONFIG"] == "/empty/user.npmrc"
    assert environment["NPM_CONFIG_GLOBALCONFIG"] == "/empty/global.npmrc"
    assert "NPM_CONFIG_REGISTRY" not in environment
    assert "npm_config_cache" not in environment
    assert "NODE_AUTH_TOKEN" not in environment
