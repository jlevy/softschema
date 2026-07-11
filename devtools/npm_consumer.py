"""Create and verify the frozen npm consumer used for artifact smoke tests."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, cast
from urllib.parse import urlsplit

REGISTRY = "https://registry.npmjs.org/"
MINIMUM_RELEASE_AGE_DAYS = 14
AUDIT_LEVEL = "moderate"
CONSUMER_NAME = "softschema-artifact-consumer"
CONSUMER_VERSION = "0.0.0"
CONTROL_NAME = "consumer-control.json"
PACKAGE_FILES = ("package.json", "package-lock.json")
BUNDLE_FILES = (*PACKAGE_FILES, CONTROL_NAME)
VERSION_PATTERN = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
    r"(?:\+[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$"
)
NPM_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
TARBALL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*\.tgz$")
INTEGRITY_PATTERN = re.compile(r"^sha512-[A-Za-z0-9+/]+={0,2}$")
CUTOFF_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")

RESOLUTION_FLAGS = [
    "--package-lock-only",
    "--ignore-scripts",
    "--no-audit",
    "--no-fund",
]
AUDIT_FLAGS = [
    "--package-lock-only",
    "--ignore-scripts",
    f"--audit-level={AUDIT_LEVEL}",
    f"--registry={REGISTRY}",
]
CI_FLAGS = [
    "ci",
    "--ignore-scripts",
    "--no-audit",
    "--no-fund",
    f"--registry={REGISTRY}",
]


class NpmConsumerError(RuntimeError):
    """A consumer resolution, lock, or install violated the release policy."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha512_integrity(path: Path) -> str:
    value = base64.b64encode(hashlib.sha512(path.read_bytes()).digest()).decode("ascii")
    return f"sha512-{value}"


def _is_sha512_integrity(value: object) -> bool:
    if not isinstance(value, str) or INTEGRITY_PATTERN.fullmatch(value) is None:
        return False
    try:
        digest = base64.b64decode(value.removeprefix("sha512-"), validate=True)
    except (ValueError, binascii.Error):
        return False
    return len(digest) == hashlib.sha512().digest_size


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(_json_text(value), encoding="utf-8")
    temporary.replace(path)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise NpmConsumerError(f"duplicate JSON key in consumer bundle: {key!r}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise NpmConsumerError(f"consumer input must be a regular file: {path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_pairs
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NpmConsumerError(f"invalid JSON consumer input: {path}") from exc
    if not isinstance(value, dict):
        raise NpmConsumerError(f"consumer input must contain an object: {path}")
    return cast(dict[str, Any], value)


def _require_tarball(tarball: Path) -> None:
    if tarball.is_symlink() or not tarball.is_file() or tarball.stat().st_size == 0:
        raise NpmConsumerError(f"npm subject must be a non-empty regular file: {tarball}")
    if TARBALL_PATTERN.fullmatch(tarball.name) is None:
        raise NpmConsumerError(f"unsafe npm subject name: {tarball.name!r}")


def _tarball_manifest(tarball: Path) -> dict[str, Any]:
    _require_tarball(tarball)
    try:
        with tarfile.open(tarball, "r:gz") as archive:
            matches = [
                member for member in archive.getmembers() if member.name == "package/package.json"
            ]
            if len(matches) != 1 or not matches[0].isfile():
                raise NpmConsumerError("npm subject must contain one regular package/package.json")
            stream = archive.extractfile(matches[0])
            if stream is None:
                raise NpmConsumerError("could not read package/package.json from npm subject")
            value = json.loads(
                stream.read().decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs
            )
    except (OSError, UnicodeError, json.JSONDecodeError, tarfile.TarError) as exc:
        raise NpmConsumerError(f"invalid npm subject: {tarball}") from exc
    if not isinstance(value, dict) or value.get("name") != "softschema":
        raise NpmConsumerError("npm subject package name must be 'softschema'")
    version = value.get("version")
    if not isinstance(version, str) or VERSION_PATTERN.fullmatch(version) is None:
        raise NpmConsumerError("npm subject has an invalid package version")
    dependencies = value.get("dependencies", {})
    if not isinstance(dependencies, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in dependencies.items()
    ):
        raise NpmConsumerError("npm subject dependencies must be a string mapping")
    return cast(dict[str, Any], value)


def _file_spec(tarball: Path) -> str:
    return f"file:../{tarball.name}"


def package_document(tarball: Path) -> dict[str, Any]:
    """Return the minimal consumer manifest for one exact local npm subject."""
    _require_tarball(tarball)
    return {
        "name": CONSUMER_NAME,
        "version": CONSUMER_VERSION,
        "private": True,
        "type": "module",
        "dependencies": {"softschema": _file_spec(tarball)},
    }


def _parse_cutoff(cutoff: str) -> datetime:
    if CUTOFF_PATTERN.fullmatch(cutoff) is None:
        raise NpmConsumerError("npm cutoff must be an exact UTC RFC3339 timestamp")
    try:
        return datetime.strptime(cutoff, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise NpmConsumerError("npm cutoff is not a valid timestamp") from exc


def _validate_cutoff(cutoff: str, *, now: datetime | None = None) -> None:
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        raise NpmConsumerError("cutoff comparison time must be timezone-aware")
    if reference.astimezone(UTC) - _parse_cutoff(cutoff) < timedelta(days=MINIMUM_RELEASE_AGE_DAYS):
        raise NpmConsumerError(f"npm cutoff must be at least {MINIMUM_RELEASE_AGE_DAYS} days old")


def _npm_environment(*, user_config: Path, global_config: Path) -> dict[str, str]:
    """Return an npm environment without caller-controlled npm configuration."""
    credential_names = {"node_auth_token", "npm_auth_token", "npm_token"}
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.casefold().startswith("npm_config_") and key.casefold() not in credential_names
    }
    environment.update(
        {
            "NPM_CONFIG_USERCONFIG": str(user_config),
            "NPM_CONFIG_GLOBALCONFIG": str(global_config),
            "NO_UPDATE_NOTIFIER": "1",
        }
    )
    return environment


def _run_npm(arguments: list[str], *, cwd: Path) -> str:
    executable = shutil.which(arguments[0])
    if executable is None:
        raise NpmConsumerError(f"npm executable is unavailable: {arguments[0]}")
    launch_arguments = [executable, *arguments[1:]]
    with tempfile.TemporaryDirectory(prefix="softschema-npm-config-") as temporary:
        config_root = Path(temporary)
        user_config = config_root / "user.npmrc"
        global_config = config_root / "global.npmrc"
        user_config.touch()
        global_config.touch()
        process = subprocess.run(
            launch_arguments,
            cwd=cwd,
            env=_npm_environment(user_config=user_config, global_config=global_config),
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            check=False,
        )
    if process.returncode != 0:
        command = " ".join(arguments)
        raise NpmConsumerError(
            f"npm command failed ({process.returncode}): {command}\n"
            f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
        )
    return process.stdout


def _validate_registry_entry(path: str, entry: dict[str, Any]) -> None:
    normalized = PurePosixPath(path)
    if (
        "\\" in path
        or path.startswith("/")
        or ".." in normalized.parts
        or normalized.as_posix() != path
    ):
        raise NpmConsumerError(f"unsafe package-lock path: {path!r}")
    if not path.startswith("node_modules/"):
        raise NpmConsumerError(f"unexpected package-lock path: {path!r}")
    version = entry.get("version")
    if not isinstance(version, str) or VERSION_PATTERN.fullmatch(version) is None:
        raise NpmConsumerError(f"registry package is not exactly versioned: {path!r}")
    resolved = entry.get("resolved")
    if not isinstance(resolved, str):
        raise NpmConsumerError(f"registry package has no resolved URL: {path!r}")
    parsed = urlsplit(resolved)
    try:
        explicit_port = parsed.port
    except ValueError as exc:
        raise NpmConsumerError(f"registry package has an invalid resolved URL: {path!r}") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != "registry.npmjs.org"
        or explicit_port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise NpmConsumerError(f"registry package resolved outside npmjs.org: {path!r}")
    integrity = entry.get("integrity")
    if not _is_sha512_integrity(integrity):
        raise NpmConsumerError(f"registry package lacks sha512 integrity: {path!r}")
    if entry.get("link") is True:
        raise NpmConsumerError(f"registry package cannot be a link: {path!r}")


def validate_package_lock(lock: dict[str, Any], tarball: Path) -> None:
    """Validate the exact local subject and every transitive registry resolution."""
    tarball_manifest = _tarball_manifest(tarball)
    expected_spec = _file_spec(tarball)
    if lock.get("name") != CONSUMER_NAME or lock.get("version") != CONSUMER_VERSION:
        raise NpmConsumerError("package-lock consumer identity does not match package.json")
    if lock.get("lockfileVersion") != 3 or lock.get("requires") is not True:
        raise NpmConsumerError("package-lock must use npm lockfileVersion 3")
    packages = lock.get("packages")
    if not isinstance(packages, dict):
        raise NpmConsumerError("package-lock has no packages mapping")
    root = packages.get("")
    if not isinstance(root, dict) or root.get("dependencies") != {"softschema": expected_spec}:
        raise NpmConsumerError("package-lock root must depend only on the exact local tarball")
    if root.get("name") != CONSUMER_NAME or root.get("version") != CONSUMER_VERSION:
        raise NpmConsumerError("package-lock root identity differs from the consumer")

    local = packages.get("node_modules/softschema")
    if not isinstance(local, dict):
        raise NpmConsumerError("package-lock does not contain the softschema subject")
    if local.get("resolved") != expected_spec:
        raise NpmConsumerError("softschema lock entry does not resolve to the exact local tarball")
    if local.get("integrity") != _sha512_integrity(tarball):
        raise NpmConsumerError("softschema lock entry has the wrong tarball integrity")
    if local.get("version") != tarball_manifest["version"]:
        raise NpmConsumerError("softschema lock entry version differs from the tarball")
    if local.get("dependencies", {}) != tarball_manifest.get("dependencies", {}):
        raise NpmConsumerError("softschema lock entry dependencies differ from the tarball")
    if local.get("link") is True:
        raise NpmConsumerError("softschema lock entry cannot be a link")

    for path, raw_entry in packages.items():
        if path in {"", "node_modules/softschema"}:
            continue
        if not isinstance(path, str) or not isinstance(raw_entry, dict):
            raise NpmConsumerError("package-lock package entries must be mappings")
        _validate_registry_entry(path, cast(dict[str, Any], raw_entry))


def _control_document(
    bundle: Path,
    tarball: Path,
    *,
    cutoff: str,
    npm_version: str,
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "subject": {
            "path": f"../{tarball.name}",
            "sha256": _sha256(tarball),
            "integrity": _sha512_integrity(tarball),
        },
        "resolution": {
            "npm_version": npm_version,
            "cutoff": cutoff,
            "minimum_release_age_days": MINIMUM_RELEASE_AGE_DAYS,
            "registry": REGISTRY,
            "flags": RESOLUTION_FLAGS,
            "configuration": {
                "ambient_npm_environment": "removed",
                "user_config": "empty_ephemeral",
                "global_config": "empty_ephemeral",
                "project_config": "absent_from_owned_bundle",
            },
        },
        "audit": {
            "level": AUDIT_LEVEL,
            "failure_policy": "fail_on_moderate_or_higher",
            "flags": AUDIT_FLAGS,
        },
        "install": {"flags": CI_FLAGS},
        "files": {name: {"sha256": _sha256(bundle / name)} for name in PACKAGE_FILES},
    }


def _bundle_inventory(bundle: Path) -> set[str]:
    if bundle.is_symlink() or not bundle.is_dir():
        raise NpmConsumerError(f"consumer bundle must be a directory: {bundle}")
    result: set[str] = set()
    for path in bundle.iterdir():
        if path.is_symlink() or not path.is_file():
            raise NpmConsumerError(f"consumer bundle contains a non-regular entry: {path}")
        result.add(path.name)
    return result


def verify_consumer_bundle(
    bundle: Path,
    tarball: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify one frozen consumer bundle and return its validated control record."""
    if _bundle_inventory(bundle) != set(BUNDLE_FILES):
        raise NpmConsumerError("consumer bundle inventory differs from the three owned files")
    package = _load_object(bundle / "package.json")
    if package != package_document(tarball):
        raise NpmConsumerError("consumer package.json differs from the exact subject binding")
    lock = _load_object(bundle / "package-lock.json")
    validate_package_lock(lock, tarball)
    control = _load_object(bundle / CONTROL_NAME)
    resolution = control.get("resolution")
    if not isinstance(resolution, dict):
        raise NpmConsumerError("consumer control has no resolution policy")
    cutoff = resolution.get("cutoff")
    npm_version = resolution.get("npm_version")
    if not isinstance(cutoff, str):
        raise NpmConsumerError("consumer control has no cutoff")
    _validate_cutoff(cutoff, now=now)
    if not isinstance(npm_version, str) or NPM_VERSION_PATTERN.fullmatch(npm_version) is None:
        raise NpmConsumerError("consumer control has no exact npm version")
    expected = _control_document(
        bundle,
        tarball,
        cutoff=cutoff,
        npm_version=npm_version,
    )
    if control != expected:
        files = control.get("files")
        if isinstance(files, dict):
            for name in PACKAGE_FILES:
                item = files.get(name)
                if isinstance(item, dict) and item.get("sha256") != _sha256(bundle / name):
                    raise NpmConsumerError(f"{name} digest differs from consumer control")
        raise NpmConsumerError("consumer control differs from the enforced policy")
    return control


def create_consumer_bundle(
    bundle: Path,
    tarball: Path,
    *,
    cutoff: str,
    expected_npm_version: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Resolve and audit a cold consumer under one pinned npm and age cutoff."""
    if NPM_VERSION_PATTERN.fullmatch(expected_npm_version) is None:
        raise NpmConsumerError("expected npm version must be an exact three-part version")
    _validate_cutoff(cutoff, now=now)
    _require_tarball(tarball)
    if bundle.exists() and (bundle.is_symlink() or not bundle.is_dir() or any(bundle.iterdir())):
        raise NpmConsumerError(f"consumer output must be absent or empty: {bundle}")
    bundle.mkdir(parents=True, exist_ok=True)
    actual_npm_version = _run_npm(["npm", "--version"], cwd=bundle).strip()
    if actual_npm_version != expected_npm_version:
        raise NpmConsumerError(
            f"expected npm {expected_npm_version}, found {actual_npm_version or 'no version'}"
        )

    _write_json(bundle / "package.json", package_document(tarball))
    _run_npm(
        [
            "npm",
            "install",
            *RESOLUTION_FLAGS,
            f"--before={cutoff}",
            f"--registry={REGISTRY}",
        ],
        cwd=bundle,
    )
    if (bundle / "node_modules").exists():
        raise NpmConsumerError("package-lock-only resolution unexpectedly created node_modules")
    validate_package_lock(_load_object(bundle / "package-lock.json"), tarball)

    # npm exits nonzero for findings at or above this threshold. Do not suppress or
    # reinterpret that exit: a moderate, high, or critical advisory blocks the candidate.
    _run_npm(["npm", "audit", *AUDIT_FLAGS], cwd=bundle)
    _write_json(
        bundle / CONTROL_NAME,
        _control_document(
            bundle,
            tarball,
            cutoff=cutoff,
            npm_version=actual_npm_version,
        ),
    )
    return verify_consumer_bundle(bundle, tarball, now=now)


def install_consumer_bundle(bundle: Path, tarball: Path, destination: Path) -> Path:
    """Copy a verified bundle and install it with frozen npm-ci semantics."""
    verify_consumer_bundle(bundle, tarball)
    if destination.exists() and (
        destination.is_symlink() or not destination.is_dir() or any(destination.iterdir())
    ):
        raise NpmConsumerError(
            f"consumer install destination must be absent or empty: {destination}"
        )
    destination.mkdir(parents=True, exist_ok=True)
    tarball_copy = destination.parent / tarball.name
    if tarball_copy.exists():
        raise NpmConsumerError(f"consumer tarball destination already exists: {tarball_copy}")
    shutil.copy2(tarball, tarball_copy)
    for name in BUNDLE_FILES:
        shutil.copy2(bundle / name, destination / name)
    before = {name: _sha256(destination / name) for name in BUNDLE_FILES}
    _run_npm(["npm", *CI_FLAGS], cwd=destination)
    after = {name: _sha256(destination / name) for name in BUNDLE_FILES}
    if after != before:
        raise NpmConsumerError("npm ci mutated the frozen consumer inputs")
    installed = destination / "node_modules" / "softschema" / "package.json"
    installed_manifest = _load_object(installed)
    subject_manifest = _tarball_manifest(tarball)
    if (
        installed_manifest.get("name") != subject_manifest["name"]
        or installed_manifest.get("version") != subject_manifest["version"]
    ):
        raise NpmConsumerError("npm ci installed a package other than the exact subject")
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="resolve, audit, and record a consumer bundle")
    create.add_argument("bundle", type=Path)
    create.add_argument("--tarball", type=Path, required=True)
    create.add_argument("--cutoff", required=True)
    create.add_argument("--npm-version", required=True)

    verify = commands.add_parser("verify", help="verify an existing consumer bundle")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("--tarball", type=Path, required=True)

    install = commands.add_parser("install", help="install a verified bundle with npm ci")
    install.add_argument("bundle", type=Path)
    install.add_argument("--tarball", type=Path, required=True)
    install.add_argument("--destination", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "create":
        result = create_consumer_bundle(
            args.bundle.resolve(),
            args.tarball.resolve(),
            cutoff=args.cutoff,
            expected_npm_version=args.npm_version,
        )
        print(_json_text(result), end="")
        return 0
    if args.command == "verify":
        print(
            _json_text(verify_consumer_bundle(args.bundle.resolve(), args.tarball.resolve())),
            end="",
        )
        return 0
    if args.command == "install":
        install_consumer_bundle(
            args.bundle.resolve(),
            args.tarball.resolve(),
            args.destination.resolve(),
        )
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
