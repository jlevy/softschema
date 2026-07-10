"""Classify immutable release state without rebuilding or publishing artifacts.

The file intentionally uses only the Python standard library so release preflight can
copy it into the frozen candidate transfer. Network adapters are read-only; workflow
steps perform any authorized mutation only after consuming a structured decision.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tarfile
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

RELEASE_MANIFEST_NAME = "release-manifest.json"
PRIMARY_CHECKSUMS_NAME = "PRIMARY-SHA256SUMS"
RELEASE_INDEX_NAME = "release-index.json"
CONTROL_FILES = (PRIMARY_CHECKSUMS_NAME, RELEASE_INDEX_NAME, RELEASE_MANIFEST_NAME)
TRANSFER_CHECKSUMS_NAME = "SHA256SUMS"
RECOVERY_BUNDLE_NAME = "release-recovery.tar"
RECOVERY_DRIVER_NAME = "release-recovery.py"
RECOVERY_CHECKSUMS_NAME = "release-recovery.sha256"
RECOVERY_ASSET_NAMES = (
    RECOVERY_BUNDLE_NAME,
    RECOVERY_CHECKSUMS_NAME,
    RECOVERY_DRIVER_NAME,
)
RESERVED_CONTROL_NAMES = frozenset({*CONTROL_FILES, TRANSFER_CHECKSUMS_NAME, *RECOVERY_ASSET_NAMES})

PACKAGE_NAME = "softschema"
PYPI_HOST = "pypi.org"
NPM_HOST = "registry.npmjs.org"
GITHUB_API_HOST = "api.github.com"
GITHUB_DOWNLOAD_HOSTS = frozenset(
    {
        GITHUB_API_HOST,
        "github.com",
        "objects.githubusercontent.com",
        "release-assets.githubusercontent.com",
    }
)
PYPI_JSON_MEDIA_TYPE = "application/json"
PYPI_INTEGRITY_MEDIA_TYPE = "application/vnd.pypi.integrity.v1+json"
GITHUB_JSON_MEDIA_TYPE = "application/vnd.github+json"
GITHUB_BINARY_MEDIA_TYPE = "application/octet-stream"
GITHUB_API_VERSION = "2026-03-10"
USER_AGENT = "softschema-release-state/1"

HTTP_TIMEOUT_SECONDS = 20
MAX_JSON_BYTES = 4_194_304
MAX_JSON_DEPTH = 128
MAX_JSON_NODES = 100_000
MAX_RELEASE_SUBJECT_BYTES = 512 * 1024 * 1024
MAX_RELEASE_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_RECOVERY_CONTENT_BYTES = MAX_RELEASE_TOTAL_BYTES + 256 * 1024 * 1024
MAX_RECOVERY_BUNDLE_BYTES = MAX_RECOVERY_CONTENT_BYTES + 32 * 1024 * 1024
MAX_RECOVERY_CHECKSUM_BYTES = 8 * 1024 * 1024
MAX_RECOVERY_FILES = 20_000
MAX_RECOVERY_NODES = MAX_RECOVERY_FILES * 2
MAX_RECOVERY_DEPTH = 32
MAX_NPM_CERTIFICATE_BYTES = 64 * 1024
MAX_DER_ELEMENTS = 2048
MAX_REDIRECTS = 3
MAX_ATTEMPTS = 20
MAX_RETRY_DELAY_SECONDS = 60.0
DEFAULT_RETRY_DELAY_SECONDS = 5.0
HTTP_NOT_FOUND = 404
HTTP_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CHECKSUM_LINE_PATTERN = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
REPOSITORY_PATTERN = re.compile(
    r"^(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/(?P<repo>[A-Za-z0-9._-]+)$"
)
VERSION_PATTERN = re.compile(
    r"^(?P<major>0|[1-9][0-9]*)\."
    r"(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)"
    r"(?:-rc\.(?P<rc>[1-9][0-9]*))?$"
)
SUPPORTED_KINDS = frozenset(
    {
        "wheel",
        "sdist",
        "npm",
        "conformance",
        "release_metadata",
        "build_metadata",
        "sbom",
    }
)
PYPI_PUBLISH_PREDICATE = "https://docs.pypi.org/attestations/publish/v1"
PYPI_TRUSTED_PUBLISHER = {
    "environment": "pypi",
    "kind": "GitHub",
    "repository": "jlevy/softschema",
    "workflow": "publish.yml",
}
NPM_PROVENANCE_PREDICATE = "https://slsa.dev/provenance/v1"
NPM_SOURCE_REPOSITORY = "https://github.com/jlevy/softschema"
NPM_SOURCE_WORKFLOW = ".github/workflows/publish.yml"


class ReleaseStateError(RuntimeError):
    """A release control, response, or immutable-state invariant failed."""


class NetworkStateError(ReleaseStateError):
    """A bounded read-only registry or release API request failed."""


@dataclass(frozen=True)
class Problem:
    """One machine-readable reason that a remote state conflicts with the manifest."""

    code: str
    name: str | None = None
    expected: str | None = None
    actual: str | None = None

    def to_dict(self) -> dict[str, str]:
        value = {"code": self.code}
        if self.name is not None:
            value["name"] = self.name
        if self.expected is not None:
            value["expected"] = self.expected
        if self.actual is not None:
            value["actual"] = self.actual
        return value


def _sorted_problems(problems: Iterable[Problem]) -> tuple[Problem, ...]:
    return tuple(
        sorted(
            problems,
            key=lambda item: (
                item.code,
                item.name or "",
                item.expected or "",
                item.actual or "",
            ),
        )
    )


@dataclass(frozen=True)
class Decision:
    """A pure classification result consumed by the release workflow."""

    state: str
    missing: tuple[str, ...] = ()
    exact: tuple[str, ...] = ()
    problems: tuple[Problem, ...] = ()
    release: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "state": self.state,
            "missing": list(self.missing),
            "exact": list(self.exact),
            "problems": [problem.to_dict() for problem in self.problems],
        }
        if self.release is not None:
            value["release"] = self.release
        return value


@dataclass(frozen=True)
class ReleaseCoordinates:
    """One logical release mapped to its ecosystem versions and channels."""

    logical_version: str
    python_version: str
    npm_version: str
    npm_tag: str
    prerelease: bool


@dataclass(frozen=True)
class Subject:
    """One immutable primary subject owned by the external release manifest."""

    name: str
    kind: str
    media_type: str
    size: int
    sha256: str


@dataclass(frozen=True)
class Manifest:
    """The validated standalone subset of release-manifest schema version 1."""

    logical_version: str
    source_commit: str
    subjects: Mapping[str, Subject]
    coordinates: ReleaseCoordinates

    def by_kind(self, *kinds: str) -> tuple[Subject, ...]:
        selected = [subject for subject in self.subjects.values() if subject.kind in kinds]
        return tuple(sorted(selected, key=lambda subject: subject.name))

    def one(self, kind: str) -> Subject:
        selected = self.by_kind(kind)
        if len(selected) != 1:
            raise ReleaseStateError(f"release manifest must contain exactly one {kind} subject")
        return selected[0]


@dataclass(frozen=True)
class ExpectedAsset:
    """One exact GitHub release asset derived from a primary or control file."""

    name: str
    size: int
    sha256: str


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha512_integrity(value: bytes) -> str:
    digest = base64.b64encode(hashlib.sha512(value).digest()).decode("ascii")
    return f"sha512-{digest}"


def _canonical_json(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        return f"{text}\n".encode("utf-8", errors="strict")
    except (TypeError, UnicodeError, ValueError) as exc:
        raise ReleaseStateError(f"cannot encode canonical control JSON: {exc}") from exc


def _validate_json_structure(value: Any, label: str) -> None:
    """Bound parsed JSON and reject escaped invalid Unicode scalar values."""
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise ReleaseStateError(f"{label}: JSON exceeds the depth limit")
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise ReleaseStateError(f"{label}: JSON exceeds the node limit")
        if isinstance(current, str):
            try:
                current.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise ReleaseStateError(
                    f"{label}: JSON contains an invalid Unicode scalar value"
                ) from exc
        elif isinstance(current, dict):
            for key in current:
                try:
                    key.encode("utf-8", errors="strict")
                except UnicodeEncodeError as exc:
                    raise ReleaseStateError(
                        f"{label}: JSON contains an invalid Unicode scalar key"
                    ) from exc
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)


def _loads_json(value: bytes, label: str) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ReleaseStateError(f"{label}: duplicate JSON key {key!r}")
            result[key] = item
        return result

    def reject_constant(constant: str) -> None:
        raise ReleaseStateError(f"{label}: non-finite JSON number {constant}")

    def parse_float(raw: str) -> float:
        parsed = float(raw)
        if not math.isfinite(parsed):
            reject_constant(raw)
        return parsed

    try:
        parsed = json.loads(
            value.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
            parse_float=parse_float,
        )
        _validate_json_structure(parsed, label)
        return parsed
    except ReleaseStateError:
        raise
    except (UnicodeError, RecursionError, ValueError) as exc:
        raise ReleaseStateError(f"{label}: invalid JSON: {exc}") from exc


def _read_json(path: Path) -> Any:
    try:
        if path.is_symlink() or not path.is_file():
            raise ReleaseStateError(f"JSON fixture must be a regular file: {path}")
        size = path.stat().st_size
        if size > MAX_JSON_BYTES:
            raise ReleaseStateError(f"JSON fixture exceeds the byte limit: {path}")
        with path.open("rb") as stream:
            value = stream.read(MAX_JSON_BYTES + 1)
        if len(value) > MAX_JSON_BYTES:
            raise ReleaseStateError(f"JSON fixture exceeds the byte limit: {path}")
        if len(value) != size:
            raise ReleaseStateError(f"JSON fixture changed while reading: {path}")
    except OSError as exc:
        raise ReleaseStateError(f"cannot read JSON fixture {path}: {exc}") from exc
    return _loads_json(value, str(path))


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReleaseStateError(f"{label} must be a JSON object")
    return cast(dict[str, Any], value)


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ReleaseStateError(
            f"{label} fields differ: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def release_coordinates(logical_version: str) -> ReleaseCoordinates:
    """Map stable and RC logical versions without importing project dependencies."""
    match = VERSION_PATTERN.fullmatch(logical_version)
    if match is None:
        raise ReleaseStateError(f"unsupported logical release version: {logical_version!r}")
    rc = match.group("rc")
    if rc is None:
        return ReleaseCoordinates(
            logical_version, logical_version, logical_version, "latest", False
        )
    base = ".".join(match.group(name) for name in ("major", "minor", "patch"))
    return ReleaseCoordinates(logical_version, f"{base}rc{rc}", logical_version, "next", True)


def load_manifest(path: Path) -> Manifest:
    """Load and strictly validate the fields needed by no-checkout release jobs."""
    raw = _require_object(_read_json(path), str(path))
    _require_exact_keys(
        raw,
        {"schema_version", "logical_version", "source_commit", "subjects"},
        "release manifest",
    )
    if raw["schema_version"] != "1":
        raise ReleaseStateError("release manifest schema_version must equal '1'")
    logical_version = raw["logical_version"]
    source_commit = raw["source_commit"]
    if not isinstance(logical_version, str):
        raise ReleaseStateError("release manifest logical_version must be a string")
    coordinates = release_coordinates(logical_version)
    if not isinstance(source_commit, str) or COMMIT_PATTERN.fullmatch(source_commit) is None:
        raise ReleaseStateError("release manifest source_commit must be a lowercase SHA-1")

    raw_subjects = _require_object(raw["subjects"], "release manifest subjects")
    if not raw_subjects:
        raise ReleaseStateError("release manifest subjects must not be empty")
    subjects: dict[str, Subject] = {}
    total_size = 0
    for name in sorted(raw_subjects):
        if SAFE_NAME_PATTERN.fullmatch(name) is None:
            raise ReleaseStateError(f"unsafe release subject filename: {name!r}")
        if name in RESERVED_CONTROL_NAMES:
            raise ReleaseStateError(f"release subject collides with a control filename: {name}")
        item = _require_object(raw_subjects[name], f"release subject {name}")
        _require_exact_keys(item, {"kind", "media_type", "size", "sha256"}, name)
        kind = item["kind"]
        media_type = item["media_type"]
        size = item["size"]
        digest = item["sha256"]
        if not isinstance(kind, str) or kind not in SUPPORTED_KINDS:
            raise ReleaseStateError(f"{name}: unsupported subject kind")
        if not isinstance(media_type, str) or not media_type:
            raise ReleaseStateError(f"{name}: media_type must be a non-empty string")
        if isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise ReleaseStateError(f"{name}: size must be a positive integer")
        if size > MAX_RELEASE_SUBJECT_BYTES:
            raise ReleaseStateError(
                f"{name}: size exceeds the {MAX_RELEASE_SUBJECT_BYTES}-byte "
                "release subject byte limit"
            )
        total_size += size
        if total_size > MAX_RELEASE_TOTAL_BYTES:
            raise ReleaseStateError(
                "release manifest exceeds the "
                f"{MAX_RELEASE_TOTAL_BYTES}-byte aggregate subject byte limit"
            )
        if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
            raise ReleaseStateError(f"{name}: sha256 must be lowercase hexadecimal")
        subjects[name] = Subject(name, kind, media_type, size, digest)

    manifest = Manifest(logical_version, source_commit, subjects, coordinates)
    package_names = {
        "wheel": f"softschema-{coordinates.python_version}-py3-none-any.whl",
        "sdist": f"softschema-{coordinates.python_version}.tar.gz",
        "npm": f"softschema-{coordinates.npm_version}.tgz",
    }
    for kind, expected_name in package_names.items():
        actual = manifest.one(kind).name
        if actual != expected_name:
            raise ReleaseStateError(
                f"{kind} filename differs from release coordinates: "
                f"expected {expected_name!r}, got {actual!r}"
            )
    return manifest


def _regular_bytes(path: Path, *, expected_size: int | None = None) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            raise ReleaseStateError(f"release input must be a regular file: {path}")
        size = path.stat().st_size
        if expected_size is not None and size != expected_size:
            raise ReleaseStateError(
                f"release input size mismatch for {path.name}: expected {expected_size}, got {size}"
            )
        value = path.read_bytes()
    except OSError as exc:
        raise ReleaseStateError(f"cannot read release input {path}: {exc}") from exc
    return value


def _bounded_regular_bytes(path: Path, *, limit: int, label: str) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            raise ReleaseStateError(f"{label} must be a regular file: {path}")
        size = path.stat().st_size
        if size > limit:
            raise ReleaseStateError(f"{label} exceeds the {limit}-byte limit")
        with path.open("rb") as stream:
            value = stream.read(limit + 1)
        if len(value) > limit:
            raise ReleaseStateError(f"{label} exceeds the {limit}-byte limit")
        if len(value) != size:
            raise ReleaseStateError(f"{label} changed while reading: {path}")
        return value
    except ReleaseStateError:
        raise
    except OSError as exc:
        raise ReleaseStateError(f"cannot read {label} {path}: {exc}") from exc


def _sha256_regular_file(
    path: Path,
    *,
    limit: int,
    expected_size: int | None = None,
) -> tuple[int, str]:
    try:
        if path.is_symlink() or not path.is_file():
            raise ReleaseStateError(f"release input must be a regular file: {path}")
        initial = path.stat().st_size
        if initial > limit:
            raise ReleaseStateError(f"release input exceeds the {limit}-byte limit: {path}")
        if expected_size is not None and initial != expected_size:
            raise ReleaseStateError(
                f"release input size mismatch for {path.name}: "
                f"expected {expected_size}, got {initial}"
            )
        digest = hashlib.sha256()
        total = 0
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                total += len(chunk)
                if total > limit:
                    raise ReleaseStateError(f"release input exceeds the {limit}-byte limit: {path}")
                digest.update(chunk)
        if total != initial or path.stat().st_size != initial:
            raise ReleaseStateError(f"release input changed while reading: {path}")
        return total, digest.hexdigest()
    except ReleaseStateError:
        raise
    except OSError as exc:
        raise ReleaseStateError(f"cannot hash release input {path}: {exc}") from exc


def _safe_recovery_path(value: str) -> str:
    path = PurePosixPath(value)
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ReleaseStateError("recovery path contains invalid Unicode") from exc
    if (
        not value
        or len(encoded) > 1024
        or "\\" in value
        or path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ReleaseStateError(f"unsafe recovery path: {value!r}")
    return value


def _recovery_parent_directories(name: str) -> tuple[str, ...]:
    parts = PurePosixPath(name).parts
    if len(parts) - 1 > MAX_RECOVERY_DEPTH:
        raise ReleaseStateError("release recovery archive exceeds the depth limit")
    return tuple(PurePosixPath(*parts[:index]).as_posix() for index in range(1, len(parts)))


def _recovery_files(directory: Path) -> dict[str, tuple[Path, int]]:
    try:
        if directory.is_symlink() or not directory.is_dir():
            raise ReleaseStateError(f"release candidate must be a directory: {directory}")
        result: dict[str, tuple[Path, int]] = {}
        total_size = 0
        entry_count = 0
        stack = [(directory, 0)]
        while stack:
            current, depth = stack.pop()
            entries = []
            with os.scandir(current) as iterator:
                for entry in iterator:
                    entry_count += 1
                    if entry_count > MAX_RECOVERY_NODES:
                        raise ReleaseStateError("release recovery tree exceeds the entry limit")
                    entries.append(entry)
            for entry in sorted(entries, key=lambda item: item.name, reverse=True):
                path = Path(entry.path)
                if entry.is_symlink():
                    raise ReleaseStateError(f"release recovery tree contains a symlink: {path}")
                if entry.is_dir(follow_symlinks=False):
                    if depth >= MAX_RECOVERY_DEPTH:
                        raise ReleaseStateError("release recovery tree exceeds the depth limit")
                    stack.append((path, depth + 1))
                    continue
                if not entry.is_file(follow_symlinks=False):
                    raise ReleaseStateError(
                        f"release recovery tree contains a special filesystem node: {path}"
                    )
                name = _safe_recovery_path(path.relative_to(directory).as_posix())
                if name in result:
                    raise ReleaseStateError(f"duplicate release recovery path: {name}")
                size = entry.stat(follow_symlinks=False).st_size
                if size < 0 or size > MAX_RECOVERY_CONTENT_BYTES:
                    raise ReleaseStateError(f"release recovery file has invalid size: {name}")
                total_size += size
                if total_size > MAX_RECOVERY_CONTENT_BYTES:
                    raise ReleaseStateError("release recovery tree exceeds the byte limit")
                result[name] = (path, size)
                if len(result) > MAX_RECOVERY_FILES:
                    raise ReleaseStateError("release recovery tree exceeds the file limit")
        return result
    except ReleaseStateError:
        raise
    except OSError as exc:
        raise ReleaseStateError(f"cannot inspect release recovery tree: {exc}") from exc


def _transfer_checksum_inventory(value: bytes) -> dict[str, str]:
    try:
        lines = value.decode("utf-8", errors="strict").splitlines()
    except UnicodeDecodeError as exc:
        raise ReleaseStateError("transfer checksum inventory is not UTF-8") from exc
    expected: dict[str, str] = {}
    for line in lines:
        match = CHECKSUM_LINE_PATTERN.fullmatch(line)
        if match is None:
            raise ReleaseStateError(f"invalid transfer checksum line: {line!r}")
        name = _safe_recovery_path(match.group(2).removeprefix("./"))
        if name == TRANSFER_CHECKSUMS_NAME:
            raise ReleaseStateError("transfer checksum inventory cannot hash itself")
        if name in expected:
            raise ReleaseStateError(f"duplicate transfer checksum path: {name}")
        expected[name] = match.group(1)
        if len(expected) > MAX_RECOVERY_FILES:
            raise ReleaseStateError("transfer checksum inventory exceeds the file limit")
    if not expected:
        raise ReleaseStateError("transfer checksum inventory is empty")
    return expected


def _verify_transfer_inventory(directory: Path) -> dict[str, tuple[Path, int]]:
    files = _recovery_files(directory)
    checksum_record = files.get(TRANSFER_CHECKSUMS_NAME)
    if checksum_record is None:
        raise ReleaseStateError("release recovery candidate has no SHA256SUMS file")
    checksum_path, _ = checksum_record
    checksum_bytes = _bounded_regular_bytes(
        checksum_path,
        limit=MAX_RECOVERY_CHECKSUM_BYTES,
        label="transfer checksum inventory",
    )
    expected = _transfer_checksum_inventory(checksum_bytes)
    actual = set(files) - {TRANSFER_CHECKSUMS_NAME}
    if set(expected) != actual:
        raise ReleaseStateError(
            "release recovery checksum inventory mismatch: "
            f"missing={sorted(set(expected) - actual)}, "
            f"extra={sorted(actual - set(expected))}"
        )
    for name in sorted(expected):
        path, size = files[name]
        _, digest = _sha256_regular_file(path, limit=size, expected_size=size)
        if digest != expected[name]:
            raise ReleaseStateError(
                f"release recovery digest mismatch for {name}: "
                f"expected {expected[name]}, got {digest}"
            )
    return files


def _recovery_bundle_metadata(path: Path) -> dict[str, Any]:
    size, digest = _sha256_regular_file(path, limit=MAX_RECOVERY_BUNDLE_BYTES)
    return {"name": path.name, "size": size, "sha256": digest}


def write_recovery_bundle(directory: Path, output: Path) -> dict[str, Any]:
    """Create a deterministic, self-verifying archive of the frozen transfer."""
    directory = directory.resolve()
    output = output.absolute()
    if output.is_relative_to(directory):
        raise ReleaseStateError("release recovery bundle must be outside the candidate")
    files = _verify_transfer_inventory(directory)
    temporary = output.with_name(f".{output.name}.tmp")
    try:
        if output.exists() or output.is_symlink():
            raise ReleaseStateError(f"release recovery output already exists: {output}")
        if output.parent.is_symlink() or not output.parent.is_dir():
            raise ReleaseStateError(
                f"release recovery output parent must be a directory: {output.parent}"
            )
        if temporary.exists() or temporary.is_symlink():
            raise ReleaseStateError(f"release recovery staging path already exists: {temporary}")
        with tarfile.open(temporary, mode="w:", format=tarfile.PAX_FORMAT) as archive:
            for name in sorted(files):
                path, size = files[name]
                info = tarfile.TarInfo(name)
                info.size = size
                info.mtime = 0
                info.mode = 0o644
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
        if temporary.stat().st_size > MAX_RECOVERY_BUNDLE_BYTES:
            raise ReleaseStateError("release recovery bundle exceeds the byte limit")
        temporary.replace(output)
        return _recovery_bundle_metadata(output)
    except ReleaseStateError:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)
        raise
    except (OSError, tarfile.TarError) as exc:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)
        raise ReleaseStateError(f"cannot create release recovery bundle: {exc}") from exc


def extract_recovery_bundle(bundle: Path, output: Path) -> dict[str, Any]:
    """Safely restore and verify an exact transfer from its durable release bundle."""
    bundle = bundle.absolute()
    output = output.absolute()
    metadata = _recovery_bundle_metadata(bundle)
    staging = output.with_name(f".{output.name}.recovery.tmp")
    try:
        if output.exists() or output.is_symlink():
            raise ReleaseStateError(f"release recovery output already exists: {output}")
        if output.parent.is_symlink() or not output.parent.is_dir():
            raise ReleaseStateError(
                f"release recovery output parent must be a directory: {output.parent}"
            )
        if staging.exists() or staging.is_symlink():
            raise ReleaseStateError(f"release recovery staging path already exists: {staging}")
        staging.mkdir()
        names: set[str] = set()
        directories: set[str] = set()
        members: list[tuple[tarfile.TarInfo, str]] = []
        total_size = 0
        with tarfile.open(bundle, mode="r:") as archive:
            for member in archive:
                if not member.isfile() or member.sparse is not None:
                    raise ReleaseStateError(
                        f"release recovery archive contains a non-regular member: {member.name}"
                    )
                name = _safe_recovery_path(member.name)
                if name in names:
                    raise ReleaseStateError(f"duplicate release recovery member: {name}")
                parents = _recovery_parent_directories(name)
                if name in directories or any(parent in names for parent in parents):
                    raise ReleaseStateError(f"conflicting release recovery member path: {name}")
                names.add(name)
                if len(names) > MAX_RECOVERY_FILES:
                    raise ReleaseStateError("release recovery archive exceeds the file limit")
                directories.update(parents)
                if len(names) + len(directories) > MAX_RECOVERY_NODES:
                    raise ReleaseStateError("release recovery archive exceeds the node limit")
                if member.size < 0 or member.size > MAX_RECOVERY_CONTENT_BYTES:
                    raise ReleaseStateError(f"release recovery member has invalid size: {name}")
                total_size += member.size
                if total_size > MAX_RECOVERY_CONTENT_BYTES:
                    raise ReleaseStateError("release recovery archive exceeds the byte limit")
                members.append((member, name))
            if not names:
                raise ReleaseStateError("release recovery archive is empty")
            for member, name in members:
                source = archive.extractfile(member)
                if source is None:
                    raise ReleaseStateError(f"cannot read release recovery member: {name}")
                target = staging.joinpath(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                remaining = member.size
                with target.open("xb") as destination:
                    while remaining:
                        chunk = source.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ReleaseStateError(f"truncated release recovery member: {name}")
                        destination.write(chunk)
                        remaining -= len(chunk)
                    if source.read(1):
                        raise ReleaseStateError(
                            f"oversized release recovery member payload: {name}"
                        )
        _verify_transfer_inventory(staging)
        staging.replace(output)
        return metadata
    except ReleaseStateError:
        with suppress(OSError):
            shutil.rmtree(staging)
        raise
    except (OSError, tarfile.TarError) as exc:
        with suppress(OSError):
            shutil.rmtree(staging)
        raise ReleaseStateError(f"cannot extract release recovery bundle: {exc}") from exc


def _verify_subject_files(directory: Path, manifest: Manifest) -> None:
    try:
        if directory.is_symlink() or not directory.is_dir():
            raise ReleaseStateError(f"release candidate must be a directory: {directory}")
    except OSError as exc:
        raise ReleaseStateError(f"cannot inspect release candidate {directory}: {exc}") from exc
    for subject in manifest.subjects.values():
        value = _regular_bytes(directory / subject.name, expected_size=subject.size)
        actual = _sha256_bytes(value)
        if actual != subject.sha256:
            raise ReleaseStateError(
                f"primary subject digest mismatch for {subject.name}: "
                f"expected {subject.sha256}, got {actual}"
            )


def _primary_checksums_bytes(manifest: Manifest) -> bytes:
    return "".join(
        f"{manifest.subjects[name].sha256}  {name}\n" for name in sorted(manifest.subjects)
    ).encode()


def _release_index_bytes(directory: Path, manifest: Manifest, primary: bytes) -> bytes:
    manifest_bytes = _regular_bytes(directory / RELEASE_MANIFEST_NAME)
    value = {
        "schema_version": "1",
        "logical_version": manifest.logical_version,
        "source_commit": manifest.source_commit,
        "release_manifest": {
            "name": RELEASE_MANIFEST_NAME,
            "sha256": _sha256_bytes(manifest_bytes),
        },
        "primary_checksums": {
            "name": PRIMARY_CHECKSUMS_NAME,
            "sha256": _sha256_bytes(primary),
        },
        "control_files": list(CONTROL_FILES),
        "github_assets": sorted([*manifest.subjects, *CONTROL_FILES]),
    }
    return _canonical_json(value)


def _atomic_write(path: Path, value: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        if path.is_symlink():
            raise ReleaseStateError(f"release control cannot replace a symlink: {path}")
        if temporary.is_symlink():
            raise ReleaseStateError(f"release control staging path is a symlink: {temporary}")
        if temporary.exists():
            if not temporary.is_file():
                raise ReleaseStateError(
                    f"release control staging path is not a regular file: {temporary}"
                )
            temporary.unlink()
        with temporary.open("xb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except ReleaseStateError:
        raise
    except OSError as exc:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)
        raise ReleaseStateError(f"cannot write release control {path}: {exc}") from exc


def write_controls(directory: Path) -> dict[str, str]:
    """Write deterministic primary checksums and an intentionally non-self-hashed index."""
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    _verify_subject_files(directory, manifest)
    primary = _primary_checksums_bytes(manifest)
    index = _release_index_bytes(directory, manifest, primary)
    _atomic_write(directory / PRIMARY_CHECKSUMS_NAME, primary)
    _atomic_write(directory / RELEASE_INDEX_NAME, index)
    return {
        PRIMARY_CHECKSUMS_NAME: _sha256_bytes(primary),
        RELEASE_INDEX_NAME: _sha256_bytes(index),
        RELEASE_MANIFEST_NAME: _sha256_bytes(_regular_bytes(directory / RELEASE_MANIFEST_NAME)),
    }


def _verify_controls(directory: Path, manifest: Manifest) -> None:
    _verify_subject_files(directory, manifest)
    primary = _primary_checksums_bytes(manifest)
    index = _release_index_bytes(directory, manifest, primary)
    for name, expected in (
        (PRIMARY_CHECKSUMS_NAME, primary),
        (RELEASE_INDEX_NAME, index),
    ):
        actual = _regular_bytes(directory / name)
        if actual != expected:
            raise ReleaseStateError(f"derived release control differs from regeneration: {name}")


def expected_github_assets(
    directory: Path,
    manifest: Manifest | None = None,
    recovery_directory: Path | None = None,
) -> dict[str, ExpectedAsset]:
    """Derive the only asset names and bytes permitted on the GitHub release."""
    actual_manifest = manifest or load_manifest(directory / RELEASE_MANIFEST_NAME)
    _verify_controls(directory, actual_manifest)
    names = sorted([*actual_manifest.subjects, *CONTROL_FILES])
    assets: dict[str, ExpectedAsset] = {}
    for name in names:
        expected_size = (
            actual_manifest.subjects[name].size if name in actual_manifest.subjects else None
        )
        size, digest = _sha256_regular_file(
            directory / name,
            limit=MAX_RELEASE_SUBJECT_BYTES,
            expected_size=expected_size,
        )
        assets[name] = ExpectedAsset(name, size, digest)
    if recovery_directory is not None:
        for name in RECOVERY_ASSET_NAMES:
            limit = (
                MAX_RECOVERY_BUNDLE_BYTES
                if name == RECOVERY_BUNDLE_NAME
                else MAX_RECOVERY_CHECKSUM_BYTES
            )
            size, digest = _sha256_regular_file(recovery_directory / name, limit=limit)
            assets[name] = ExpectedAsset(name, size, digest)
    return assets


def classify_pypi(manifest: Manifest, payload: Any | None) -> Decision:
    """Classify the exact PyPI wheel/sdist set without performing a mutation."""
    expected = {subject.name: subject for subject in manifest.by_kind("wheel", "sdist")}
    if payload is None:
        return Decision("absent", missing=tuple(sorted(expected)))
    problems: list[Problem] = []
    exact: set[str] = set()
    if not isinstance(payload, dict):
        return Decision("conflict", problems=(Problem("invalid_response"),))
    info = payload.get("info")
    if not isinstance(info, dict) or info.get("version") != manifest.coordinates.python_version:
        problems.append(
            Problem(
                "version_mismatch",
                expected=manifest.coordinates.python_version,
                actual=str(info.get("version") if isinstance(info, dict) else None),
            )
        )
    urls = payload.get("urls")
    if not isinstance(urls, list):
        problems.append(Problem("invalid_file_list"))
        urls = []
    records: dict[str, list[dict[str, Any]]] = {}
    for raw in urls:
        if not isinstance(raw, dict):
            problems.append(Problem("invalid_file_record"))
            continue
        name = raw.get("filename")
        if not isinstance(name, str):
            problems.append(Problem("invalid_filename"))
            continue
        records.setdefault(name, []).append(cast(dict[str, Any], raw))
    for name in sorted(records):
        named_records = records[name]
        subject = expected.get(name)
        if subject is None:
            problems.append(Problem("unexpected_filename", name=name))
        if len(named_records) != 1:
            problems.append(Problem("duplicate_filename", name=name))
            continue
        if subject is None:
            continue
        raw = named_records[0]
        record_exact = True
        yanked = raw.get("yanked")
        if not isinstance(yanked, bool):
            problems.append(Problem("invalid_yanked", name=name, actual=str(yanked)))
            record_exact = False
        elif yanked:
            problems.append(Problem("yanked_file", name=name))
            record_exact = False
        size = raw.get("size")
        if isinstance(size, bool) or not isinstance(size, int):
            problems.append(Problem("invalid_size", name=name, actual=str(size)))
            record_exact = False
        elif size != subject.size:
            problems.append(
                Problem(
                    "size_mismatch",
                    name=name,
                    expected=str(subject.size),
                    actual=str(size),
                )
            )
            record_exact = False
        digests = raw.get("digests")
        actual = digests.get("sha256") if isinstance(digests, dict) else None
        if actual != subject.sha256:
            problems.append(
                Problem(
                    "digest_mismatch",
                    name=name,
                    expected=subject.sha256,
                    actual=str(actual),
                )
            )
            record_exact = False
        if record_exact:
            exact.add(name)
    missing = tuple(sorted(set(expected) - exact))
    if problems:
        return Decision(
            "conflict",
            missing=missing,
            exact=tuple(sorted(exact)),
            problems=_sorted_problems(problems),
        )
    if not exact:
        return Decision(
            "conflict",
            missing=missing,
            problems=(Problem("empty_existing_version"),),
        )
    if missing:
        return Decision("partial", missing=missing, exact=tuple(sorted(exact)))
    return Decision("complete", exact=tuple(sorted(exact)))


def _validated_https_url(url: str, allowed_hosts: frozenset[str]) -> str:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ReleaseStateError(f"invalid HTTPS URL: {url!r}") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname not in allowed_hosts
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ReleaseStateError(f"URL is outside the fixed HTTPS origins: {url!r}")
    return url


def _npm_tarball_url(subject: Subject) -> str:
    return f"https://{NPM_HOST}/{PACKAGE_NAME}/-/{subject.name}"


def classify_npm(
    manifest: Manifest,
    payload: Any | None,
    tarball_bytes: bytes | None,
    *,
    packument: Any | None = None,
    require_channel: bool = False,
) -> Decision:
    """Classify one immutable npm version by metadata, SRI, and downloaded bytes."""
    subject = manifest.one("npm")
    if payload is None:
        return Decision("absent", missing=(subject.name,))
    problems: list[Problem] = []
    if not isinstance(payload, dict):
        return Decision("conflict", problems=(Problem("invalid_response"),))
    if payload.get("name") != PACKAGE_NAME:
        problems.append(
            Problem("package_name_mismatch", expected=PACKAGE_NAME, actual=str(payload.get("name")))
        )
    if payload.get("version") != manifest.coordinates.npm_version:
        problems.append(
            Problem(
                "version_mismatch",
                expected=manifest.coordinates.npm_version,
                actual=str(payload.get("version")),
            )
        )
    dist = payload.get("dist")
    if not isinstance(dist, dict):
        problems.append(Problem("invalid_dist"))
        dist = {}
    expected_url = _npm_tarball_url(subject)
    actual_url = dist.get("tarball")
    if actual_url != expected_url:
        problems.append(
            Problem("tarball_url_mismatch", expected=expected_url, actual=str(actual_url))
        )
    elif isinstance(actual_url, str):
        try:
            _validated_https_url(actual_url, frozenset({NPM_HOST}))
        except ReleaseStateError:
            problems.append(Problem("tarball_url_mismatch", actual=actual_url))
    if tarball_bytes is None:
        problems.append(Problem("missing_tarball_bytes", name=subject.name))
    else:
        actual_digest = _sha256_bytes(tarball_bytes)
        if len(tarball_bytes) != subject.size:
            problems.append(
                Problem(
                    "size_mismatch",
                    name=subject.name,
                    expected=str(subject.size),
                    actual=str(len(tarball_bytes)),
                )
            )
        if actual_digest != subject.sha256:
            problems.append(
                Problem(
                    "digest_mismatch",
                    name=subject.name,
                    expected=subject.sha256,
                    actual=actual_digest,
                )
            )
        expected_integrity = _sha512_integrity(tarball_bytes)
        if dist.get("integrity") != expected_integrity:
            problems.append(
                Problem(
                    "integrity_mismatch",
                    name=subject.name,
                    expected=expected_integrity,
                    actual=str(dist.get("integrity")),
                )
            )
        shasum = dist.get("shasum")
        actual_shasum = hashlib.sha1(tarball_bytes, usedforsecurity=False).hexdigest()
        if shasum is not None and (not isinstance(shasum, str) or shasum != actual_shasum):
            problems.append(
                Problem(
                    "registry_shasum_mismatch",
                    name=subject.name,
                    expected=actual_shasum,
                    actual=str(shasum),
                )
            )
    if require_channel:
        tags = packument.get("dist-tags") if isinstance(packument, dict) else None
        actual_tag = tags.get(manifest.coordinates.npm_tag) if isinstance(tags, dict) else None
        if actual_tag != manifest.coordinates.npm_version:
            problems.append(
                Problem(
                    "dist_tag_mismatch",
                    name=manifest.coordinates.npm_tag,
                    expected=manifest.coordinates.npm_version,
                    actual=str(actual_tag),
                )
            )
        if (
            manifest.coordinates.prerelease
            and isinstance(tags, dict)
            and tags.get("latest") == manifest.coordinates.npm_version
        ):
            problems.append(
                Problem(
                    "prerelease_is_latest",
                    name="latest",
                    actual=manifest.coordinates.npm_version,
                )
            )
    if problems:
        return Decision("conflict", problems=_sorted_problems(problems))
    return Decision("complete", exact=(subject.name,))


def classify_github(
    manifest: Manifest,
    expected: Mapping[str, ExpectedAsset],
    payload: Any | None,
    fallback_digests: Mapping[str, str] | None = None,
) -> Decision:
    """Classify a draft or already-published GitHub release asset inventory."""
    expected_names = set(expected)
    if payload is None:
        return Decision("missing", missing=tuple(sorted(expected_names)), release="absent")
    if not isinstance(payload, dict):
        return Decision("conflict", problems=(Problem("invalid_response"),))
    draft = payload.get("draft")
    release = "draft" if draft is True else "published" if draft is False else "invalid"
    problems: list[Problem] = []
    if payload.get("tag_name") != f"v{manifest.logical_version}":
        problems.append(
            Problem(
                "tag_mismatch",
                expected=f"v{manifest.logical_version}",
                actual=str(payload.get("tag_name")),
            )
        )
    if payload.get("prerelease") is not manifest.coordinates.prerelease:
        problems.append(
            Problem(
                "prerelease_mismatch",
                expected=str(manifest.coordinates.prerelease).lower(),
                actual=str(payload.get("prerelease")).lower(),
            )
        )
    if release == "invalid":
        problems.append(Problem("invalid_draft_flag"))
    if release == "published" and payload.get("immutable") is not True:
        problems.append(
            Problem(
                "published_release_not_immutable",
                expected="true",
                actual=str(payload.get("immutable")).lower(),
            )
        )
    assets = payload.get("assets")
    if not isinstance(assets, list):
        problems.append(Problem("invalid_asset_list"))
        assets = []
    exact: set[str] = set()
    unexpected: list[Problem] = []
    fallback = fallback_digests or {}
    records: dict[str, list[dict[str, Any]]] = {}
    for raw in assets:
        if not isinstance(raw, dict):
            problems.append(Problem("invalid_asset_record"))
            continue
        name = raw.get("name")
        if not isinstance(name, str):
            problems.append(Problem("invalid_asset_name"))
            continue
        records.setdefault(name, []).append(cast(dict[str, Any], raw))
    for name in sorted(records):
        named_records = records[name]
        item = expected.get(name)
        if item is None:
            unexpected.append(Problem("unexpected_asset", name=name))
        if len(named_records) != 1:
            problems.append(Problem("duplicate_asset", name=name))
            continue
        if item is None:
            continue
        raw = named_records[0]
        if raw.get("state") != "uploaded":
            problems.append(Problem("asset_not_uploaded", name=name, actual=str(raw.get("state"))))
            continue
        size = raw.get("size")
        if isinstance(size, bool) or not isinstance(size, int) or size != item.size:
            problems.append(
                Problem(
                    "size_mismatch",
                    name=name,
                    expected=str(item.size),
                    actual=str(size),
                )
            )
            continue
        digest = raw.get("digest")
        actual_digest: str | None
        if isinstance(digest, str) and digest.startswith("sha256:"):
            actual_digest = digest.removeprefix("sha256:")
        elif digest is None:
            actual_digest = fallback.get(name)
        else:
            actual_digest = None
        if actual_digest != item.sha256:
            problems.append(
                Problem(
                    "digest_mismatch",
                    name=name,
                    expected=item.sha256,
                    actual=str(actual_digest),
                )
            )
            continue
        exact.add(name)
    missing = tuple(sorted(expected_names - exact))
    if unexpected:
        return Decision(
            "unexpected",
            missing=missing,
            exact=tuple(sorted(exact)),
            problems=_sorted_problems([*unexpected, *problems]),
            release=release,
        )
    if release == "published" and missing and not problems:
        problems.append(Problem("published_release_missing_assets"))
    if problems:
        return Decision(
            "conflict",
            missing=missing,
            exact=tuple(sorted(exact)),
            problems=_sorted_problems(problems),
            release=release,
        )
    if missing:
        return Decision("missing", missing=missing, exact=tuple(sorted(exact)), release=release)
    return Decision("exact", exact=tuple(sorted(exact)), release=release)


def classify_github_latest(manifest: Manifest, payload: Any | None) -> tuple[Problem, ...]:
    """Classify the stable latest pointer without letting an RC displace it."""
    expected_tag = f"v{manifest.logical_version}"
    if payload is None:
        if manifest.coordinates.prerelease:
            return ()
        return (Problem("latest_release_absent", expected=expected_tag),)
    if not isinstance(payload, dict) or not isinstance(payload.get("tag_name"), str):
        return (Problem("invalid_latest_response"),)
    actual_tag = cast(str, payload["tag_name"])
    if manifest.coordinates.prerelease:
        if actual_tag == expected_tag:
            return (
                Problem(
                    "prerelease_is_latest",
                    name="latest",
                    actual=actual_tag,
                ),
            )
        return ()
    if actual_tag != expected_tag:
        return (
            Problem(
                "latest_tag_mismatch",
                name="latest",
                expected=expected_tag,
                actual=actual_tag,
            ),
        )
    return ()


def _statement_attests(value: Any, subject: Subject) -> bool:
    if (
        not isinstance(value, dict)
        or value.get("_type") != "https://in-toto.io/Statement/v1"
        or value.get("predicateType") != PYPI_PUBLISH_PREDICATE
        or "predicate" not in value
        or value.get("predicate") not in (None, {})
    ):
        return False
    raw_subjects = value.get("subject")
    if not isinstance(raw_subjects, list):
        return False
    for item in raw_subjects:
        if not isinstance(item, dict) or item.get("name") != subject.name:
            continue
        digest = item.get("digest")
        if isinstance(digest, dict) and digest.get("sha256") == subject.sha256:
            return True
    return False


def check_pypi_integrity_metadata(manifest: Manifest, payloads: Mapping[str, Any]) -> None:
    """Check PyPI Integrity API publisher metadata and stated subject digests.

    This is a metadata policy check, not independent cryptographic verification of
    the returned attestations.
    """
    for subject in manifest.by_kind("wheel", "sdist"):
        payload = payloads.get(subject.name)
        if not isinstance(payload, dict):
            raise ReleaseStateError(f"PyPI Integrity API metadata is absent for {subject.name}")
        if payload.get("version") != 1:
            raise ReleaseStateError(
                f"PyPI Integrity API metadata has an unsupported version for {subject.name}"
            )
        bundles = payload.get("attestation_bundles")
        if not isinstance(bundles, list):
            raise ReleaseStateError(f"PyPI Integrity API metadata is malformed for {subject.name}")
        matched = False
        for bundle in bundles:
            publisher = bundle.get("publisher") if isinstance(bundle, dict) else None
            if not isinstance(publisher, dict) or any(
                publisher.get(key) != value for key, value in PYPI_TRUSTED_PUBLISHER.items()
            ):
                continue
            attestations = bundle.get("attestations") if isinstance(bundle, dict) else None
            if not isinstance(attestations, list):
                continue
            for attestation in attestations:
                envelope = attestation.get("envelope") if isinstance(attestation, dict) else None
                encoded = envelope.get("statement") if isinstance(envelope, dict) else None
                if not isinstance(encoded, str):
                    continue
                try:
                    statement_bytes = base64.b64decode(encoded, validate=True)
                    statement = _loads_json(statement_bytes, f"PyPI statement for {subject.name}")
                except (binascii.Error, ReleaseStateError):
                    continue
                if _statement_attests(statement, subject):
                    matched = True
                    break
            if matched:
                break
        if not matched:
            raise ReleaseStateError(
                "PyPI Integrity API metadata has no exact trusted publisher and "
                f"manifest subject match for {subject.name}"
            )


def _npm_statement_matches(
    statement: Any,
    manifest: Manifest,
    tarball: bytes,
) -> bool:
    if (
        not isinstance(statement, dict)
        or statement.get("_type") != "https://in-toto.io/Statement/v1"
        or statement.get("predicateType") != NPM_PROVENANCE_PREDICATE
    ):
        return False
    subjects = statement.get("subject")
    expected_purl = f"pkg:npm/{PACKAGE_NAME}@{manifest.coordinates.npm_version}"
    expected_sha512 = hashlib.sha512(tarball).hexdigest()
    if not isinstance(subjects, list) or not any(
        isinstance(item, dict)
        and item.get("name") == expected_purl
        and isinstance(item.get("digest"), dict)
        and item["digest"].get("sha512") == expected_sha512
        for item in subjects
    ):
        return False
    predicate = statement.get("predicate")
    build_definition = predicate.get("buildDefinition") if isinstance(predicate, dict) else None
    external = (
        build_definition.get("externalParameters") if isinstance(build_definition, dict) else None
    )
    workflow = external.get("workflow") if isinstance(external, dict) else None
    return isinstance(workflow, dict) and all(
        (
            workflow.get("repository") == NPM_SOURCE_REPOSITORY,
            workflow.get("path") == NPM_SOURCE_WORKFLOW,
            workflow.get("ref") == f"refs/tags/v{manifest.logical_version}",
        )
    )


def _der_element(data: bytes, offset: int, limit: int) -> tuple[int, int, int, int]:
    """Read one bounded DER TLV with canonical definite-length encoding."""
    if offset >= limit:
        raise ValueError("missing DER tag")
    tag = data[offset]
    if tag & 0x1F == 0x1F:
        raise ValueError("high-tag DER values are unsupported")
    offset += 1
    if offset >= limit:
        raise ValueError("missing DER length")
    first = data[offset]
    offset += 1
    if first < 0x80:
        length = first
    else:
        count = first & 0x7F
        if count == 0 or count > 4 or offset + count > limit:
            raise ValueError("invalid DER length")
        encoded = data[offset : offset + count]
        if encoded[0] == 0:
            raise ValueError("non-canonical DER length")
        length = int.from_bytes(encoded)
        if length < 0x80:
            raise ValueError("non-canonical DER length")
        offset += count
    end = offset + length
    if end > limit:
        raise ValueError("DER value exceeds its container")
    return tag, offset, end, end


def _der_children(data: bytes, start: int, end: int) -> list[tuple[int, int, int]]:
    children: list[tuple[int, int, int]] = []
    offset = start
    while offset < end:
        if len(children) >= MAX_DER_ELEMENTS:
            raise ValueError("DER element limit exceeded")
        tag, value_start, value_end, offset = _der_element(data, offset, end)
        children.append((tag, value_start, value_end))
    if offset != end:
        raise ValueError("DER container length mismatch")
    return children


def _certificate_uri_identities(certificate: bytes) -> tuple[str, ...]:
    """Return URI SAN claims from one structurally valid DER X.509 certificate."""
    tag, start, end, next_offset = _der_element(certificate, 0, len(certificate))
    if tag != 0x30 or next_offset != len(certificate):
        raise ValueError("certificate is not one DER sequence")
    certificate_fields = _der_children(certificate, start, end)
    if len(certificate_fields) != 3 or tuple(field[0] for field in certificate_fields) != (
        0x30,
        0x30,
        0x03,
    ):
        raise ValueError("certificate has invalid fields")
    _, tbs_start, tbs_end = certificate_fields[0]
    tbs_fields = _der_children(certificate, tbs_start, tbs_end)
    index = 1 if tbs_fields and tbs_fields[0][0] == 0xA0 else 0
    required_tags = (0x02, 0x30, 0x30, 0x30, 0x30, 0x30)
    if tuple(field[0] for field in tbs_fields[index : index + 6]) != required_tags:
        raise ValueError("certificate TBS fields are invalid")
    extension_fields = [field for field in tbs_fields[index + 6 :] if field[0] == 0xA3]
    if len(extension_fields) != 1:
        raise ValueError("certificate must have one extensions field")
    _, extensions_start, extensions_end = extension_fields[0]
    wrapper = _der_children(certificate, extensions_start, extensions_end)
    if len(wrapper) != 1 or wrapper[0][0] != 0x30:
        raise ValueError("certificate extensions are malformed")
    extensions = _der_children(certificate, wrapper[0][1], wrapper[0][2])
    san_values: list[bytes] = []
    for extension_tag, extension_start, extension_end in extensions:
        if extension_tag != 0x30:
            raise ValueError("certificate extension is malformed")
        fields = _der_children(certificate, extension_start, extension_end)
        if len(fields) not in {2, 3} or fields[0][0] != 0x06:
            raise ValueError("certificate extension fields are malformed")
        value_index = 2 if len(fields) == 3 and fields[1][0] == 0x01 else 1
        if value_index != len(fields) - 1 or fields[value_index][0] != 0x04:
            raise ValueError("certificate extension value is malformed")
        oid = certificate[fields[0][1] : fields[0][2]]
        if oid == b"\x55\x1d\x11":
            san_values.append(certificate[fields[value_index][1] : fields[value_index][2]])
    if len(san_values) != 1:
        raise ValueError("certificate must have one subjectAltName extension")
    san = san_values[0]
    san_tag, san_start, san_end, san_next = _der_element(san, 0, len(san))
    if san_tag != 0x30 or san_next != len(san):
        raise ValueError("certificate subjectAltName is malformed")
    identities: list[str] = []
    for name_tag, name_start, name_end in _der_children(san, san_start, san_end):
        if name_tag != 0x86:
            continue
        identities.append(san[name_start:name_end].decode("ascii", errors="strict"))
    return tuple(identities)


def _npm_certificate_has_source_identity(bundle: Mapping[str, Any], manifest: Manifest) -> bool:
    verification = bundle.get("verificationMaterial")
    if not isinstance(verification, dict):
        return False
    raw: Any = None
    certificate = verification.get("certificate")
    if isinstance(certificate, dict):
        raw = certificate.get("rawBytes")
    else:
        chain = verification.get("x509CertificateChain")
        certificates = chain.get("certificates") if isinstance(chain, dict) else None
        if isinstance(certificates, list) and certificates and isinstance(certificates[0], dict):
            raw = certificates[0].get("rawBytes")
    if not isinstance(raw, str) or len(raw) > ((MAX_NPM_CERTIFICATE_BYTES + 2) // 3) * 4 + 4:
        return False
    try:
        certificate_bytes = base64.b64decode(raw, validate=True)
        if len(certificate_bytes) > MAX_NPM_CERTIFICATE_BYTES:
            return False
        identities = _certificate_uri_identities(certificate_bytes)
    except (UnicodeError, ValueError, binascii.Error):
        return False
    identity = (
        f"{NPM_SOURCE_REPOSITORY}/{NPM_SOURCE_WORKFLOW}@refs/tags/v{manifest.logical_version}"
    )
    return identities == (identity,)


def check_npm_audit_attestations(
    directory: Path,
    manifest: Manifest,
    report: Any,
) -> None:
    """Enforce policy on npm 11's already-verified attestation report."""
    if not isinstance(report, dict):
        raise ReleaseStateError("npm audit signatures report must be a JSON object")
    records: dict[str, list[dict[str, Any]]] = {}
    for key in ("invalid", "missing", "verified"):
        value = report.get(key)
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise ReleaseStateError(f"npm audit signatures report has an invalid {key!r} list")
        records[key] = cast(list[dict[str, Any]], value)
    if records["invalid"] or records["missing"]:
        raise ReleaseStateError(
            "npm audit signatures reported invalid or missing registry evidence"
        )
    version = manifest.coordinates.npm_version
    matches = [
        item
        for item in records["verified"]
        if item.get("name") == PACKAGE_NAME and item.get("version") == version
    ]
    if len(matches) != 1:
        raise ReleaseStateError(
            f"npm audit signatures must report exactly one verified {PACKAGE_NAME}@{version}"
        )
    subject = manifest.one("npm")
    tarball = _regular_bytes(directory / subject.name, expected_size=subject.size)
    if _sha256_bytes(tarball) != subject.sha256:
        raise ReleaseStateError("npm candidate bytes differ from the release manifest")
    bundles = matches[0].get("attestationBundles")
    if not isinstance(bundles, list) or not bundles:
        raise ReleaseStateError(
            f"npm audit signatures reported no attestations for {PACKAGE_NAME}@{version}"
        )
    for item in bundles:
        if not isinstance(item, dict) or item.get("predicateType") != NPM_PROVENANCE_PREDICATE:
            continue
        bundle = item.get("bundle")
        envelope = bundle.get("dsseEnvelope") if isinstance(bundle, dict) else None
        encoded = envelope.get("payload") if isinstance(envelope, dict) else None
        if not isinstance(bundle, dict) or not isinstance(encoded, str):
            continue
        try:
            statement = _loads_json(
                base64.b64decode(encoded, validate=True),
                f"npm provenance statement for {PACKAGE_NAME}@{version}",
            )
        except (binascii.Error, ReleaseStateError):
            continue
        if _npm_statement_matches(statement, manifest, tarball) and (
            _npm_certificate_has_source_identity(bundle, manifest)
        ):
            return
    raise ReleaseStateError(
        "npm audit signatures has no verified SLSA provenance from the exact trusted "
        f"source identity for {PACKAGE_NAME}@{version}"
    )


# The transferred helper cannot depend on `typing_extensions` only to mark this override.
class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(  # pyright: ignore[reportImplicitOverride]
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _download(
    url: str,
    *,
    allowed_hosts: frozenset[str],
    limit: int,
    headers: Mapping[str, str] | None = None,
    allow_not_found: bool = False,
) -> bytes | None:
    current = _validated_https_url(url, allowed_hosts)
    origin_host = urlsplit(current).hostname
    opener = build_opener(_NoRedirect)
    request_headers = {"User-Agent": USER_AGENT, **dict(headers or {})}
    for redirect_count in range(MAX_REDIRECTS + 1):
        host = urlsplit(current).hostname
        safe_headers = dict(request_headers)
        if host != origin_host:
            safe_headers.pop("Authorization", None)
        request = Request(current, headers=safe_headers, method="GET")
        try:
            with opener.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    if not content_length.isascii() or not content_length.isdecimal():
                        raise NetworkStateError("HTTP response has an invalid Content-Length")
                    declared = int(content_length)
                    if declared > limit:
                        raise NetworkStateError("HTTP response exceeds the configured byte limit")
                value = response.read(limit + 1)
                if len(value) > limit:
                    raise NetworkStateError("HTTP response exceeds the configured byte limit")
                return value
        except HTTPError as exc:
            if exc.code == HTTP_NOT_FOUND and allow_not_found:
                return None
            if exc.code in HTTP_REDIRECT_STATUSES:
                if redirect_count == MAX_REDIRECTS:
                    raise NetworkStateError("HTTP redirect limit exceeded") from exc
                location = exc.headers.get("Location")
                if not location:
                    raise NetworkStateError("HTTP redirect omitted Location") from exc
                current = _validated_https_url(urljoin(current, location), allowed_hosts)
                continue
            raise NetworkStateError(f"HTTP request failed with status {exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise NetworkStateError(f"HTTPS request failed: {exc}") from exc
    raise AssertionError("redirect loop exhausted without returning")


def _download_json(
    url: str,
    *,
    host: str,
    media_type: str = PYPI_JSON_MEDIA_TYPE,
    headers: Mapping[str, str] | None = None,
    allow_not_found: bool = False,
) -> Any | None:
    value = _download(
        url,
        allowed_hosts=frozenset({host}),
        limit=MAX_JSON_BYTES,
        headers={"Accept": media_type, **dict(headers or {})},
        allow_not_found=allow_not_found,
    )
    if value is None:
        return None
    return _loads_json(value, url)


def _pypi_payload(manifest: Manifest, fixture: Path | None) -> Any | None:
    if fixture is not None:
        return _read_json(fixture)
    version = quote(manifest.coordinates.python_version, safe="")
    return _download_json(
        f"https://{PYPI_HOST}/pypi/{PACKAGE_NAME}/{version}/json",
        host=PYPI_HOST,
        allow_not_found=True,
    )


def _pypi_provenance_payloads(
    manifest: Manifest,
    fixture_directory: Path | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for subject in manifest.by_kind("wheel", "sdist"):
        if fixture_directory is not None:
            result[subject.name] = _read_json(fixture_directory / f"{subject.name}.json")
            continue
        version = quote(manifest.coordinates.python_version, safe="")
        filename = quote(subject.name, safe="")
        value = _download_json(
            f"https://{PYPI_HOST}/integrity/{PACKAGE_NAME}/{version}/{filename}/provenance",
            host=PYPI_HOST,
            media_type=PYPI_INTEGRITY_MEDIA_TYPE,
            allow_not_found=True,
        )
        if value is None:
            raise NetworkStateError(f"PyPI provenance is not yet available for {subject.name}")
        result[subject.name] = value
    return result


def _npm_payloads(
    manifest: Manifest,
    fixture: Path | None,
    tarball_fixture: Path | None,
    packument_fixture: Path | None,
    *,
    require_channel: bool,
) -> tuple[Any | None, bytes | None, Any | None]:
    version = quote(manifest.coordinates.npm_version, safe="")
    payload = (
        _read_json(fixture)
        if fixture is not None
        else _download_json(
            f"https://{NPM_HOST}/{PACKAGE_NAME}/{version}",
            host=NPM_HOST,
            allow_not_found=True,
        )
    )
    tarball: bytes | None = None
    if payload is not None:
        if tarball_fixture is not None:
            tarball = _regular_bytes(tarball_fixture)
        else:
            raw_dist = payload.get("dist") if isinstance(payload, dict) else None
            tarball_url = raw_dist.get("tarball") if isinstance(raw_dist, dict) else None
            if not isinstance(tarball_url, str):
                raise ReleaseStateError("npm version metadata has no tarball URL")
            subject = manifest.one("npm")
            if tarball_url == _npm_tarball_url(subject):
                tarball = _download(
                    tarball_url,
                    allowed_hosts=frozenset({NPM_HOST}),
                    limit=subject.size,
                )
    packument: Any | None = None
    if require_channel:
        packument = (
            _read_json(packument_fixture)
            if packument_fixture is not None
            else _download_json(f"https://{NPM_HOST}/{PACKAGE_NAME}", host=NPM_HOST)
        )
    return payload, tarball, packument


def _github_payloads(
    manifest: Manifest,
    expected: Mapping[str, ExpectedAsset],
    repository: str,
    tag: str,
    fixture: Path | None,
    asset_fixtures: Path | None,
    token: str | None,
) -> tuple[Any | None, dict[str, str]]:
    match = REPOSITORY_PATTERN.fullmatch(repository)
    if match is None:
        raise ReleaseStateError(f"invalid GitHub repository coordinate: {repository!r}")
    expected_tag = f"v{manifest.logical_version}"
    if tag != expected_tag:
        raise ReleaseStateError(f"release tag must equal {expected_tag!r}")
    owner = quote(match.group("owner"), safe="")
    repo = quote(match.group("repo"), safe="")
    encoded_tag = quote(tag, safe="")
    headers = {
        "Accept": GITHUB_JSON_MEDIA_TYPE,
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = (
        _read_json(fixture)
        if fixture is not None
        else _download_json(
            f"https://{GITHUB_API_HOST}/repos/{owner}/{repo}/releases/tags/{encoded_tag}",
            host=GITHUB_API_HOST,
            media_type=GITHUB_JSON_MEDIA_TYPE,
            headers=headers,
            allow_not_found=True,
        )
    )
    fallback: dict[str, str] = {}
    assets = payload.get("assets") if isinstance(payload, dict) else None
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict) or asset.get("digest") is not None:
                continue
            name = asset.get("name")
            if (
                not isinstance(name, str)
                or SAFE_NAME_PATTERN.fullmatch(name) is None
                or name not in expected
            ):
                continue
            expected_asset = expected[name]
            asset_size = asset.get("size")
            if (
                isinstance(asset_size, bool)
                or not isinstance(asset_size, int)
                or asset_size != expected_asset.size
            ):
                continue
            if asset_fixtures is not None:
                value = _regular_bytes(
                    asset_fixtures / name,
                    expected_size=expected_asset.size,
                )
            else:
                asset_url = asset.get("url")
                if not isinstance(asset_url, str):
                    continue
                asset_id = asset.get("id")
                expected_prefix = f"https://{GITHUB_API_HOST}/repos/{owner}/{repo}/releases/assets/"
                if (
                    isinstance(asset_id, bool)
                    or not isinstance(asset_id, int)
                    or asset_id < 1
                    or asset_url != f"{expected_prefix}{asset_id}"
                ):
                    continue
                value = _download(
                    asset_url,
                    allowed_hosts=GITHUB_DOWNLOAD_HOSTS,
                    limit=expected_asset.size,
                    headers={**headers, "Accept": GITHUB_BINARY_MEDIA_TYPE},
                )
                if value is None:
                    continue
            fallback[name] = _sha256_bytes(value)
    return payload, fallback


def _github_latest_payload(
    repository: str,
    fixture: Path | None,
    token: str | None,
) -> Any | None:
    match = REPOSITORY_PATTERN.fullmatch(repository)
    if match is None:
        raise ReleaseStateError(f"invalid GitHub repository coordinate: {repository!r}")
    if fixture is not None:
        return _read_json(fixture)
    owner = quote(match.group("owner"), safe="")
    repo = quote(match.group("repo"), safe="")
    headers = {
        "Accept": GITHUB_JSON_MEDIA_TYPE,
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _download_json(
        f"https://{GITHUB_API_HOST}/repos/{owner}/{repo}/releases/latest",
        host=GITHUB_API_HOST,
        media_type=GITHUB_JSON_MEDIA_TYPE,
        headers=headers,
        allow_not_found=True,
    )


def _empty_output_directory(path: Path) -> None:
    try:
        if path.exists():
            if path.is_symlink() or not path.is_dir() or any(path.iterdir()):
                raise ReleaseStateError(f"output directory must be absent or empty: {path}")
        else:
            path.mkdir(parents=True)
    except OSError as exc:
        raise ReleaseStateError(f"cannot prepare output directory {path}: {exc}") from exc


def stage_pypi(directory: Path, plan_path: Path, output: Path) -> None:
    """Copy only manifest-selected missing PyPI subjects into an empty directory."""
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    plan = _require_object(_read_json(plan_path), "PyPI plan")
    _require_exact_keys(plan, {"state", "missing", "exact", "problems"}, "PyPI plan")
    state = plan.get("state")
    if state not in {"absent", "partial"}:
        raise ReleaseStateError("PyPI staging requires an absent or partial plan")
    missing = plan.get("missing")
    exact = plan.get("exact")
    problems = plan.get("problems")
    if (
        not isinstance(missing, list)
        or not all(isinstance(name, str) for name in missing)
        or not isinstance(exact, list)
        or not all(isinstance(name, str) for name in exact)
        or problems != []
    ):
        raise ReleaseStateError("PyPI plan has invalid structured fields")
    expected = {subject.name for subject in manifest.by_kind("wheel", "sdist")}
    names = cast(list[str], missing)
    exact_names = cast(list[str], exact)
    missing_set = set(names)
    exact_set = set(exact_names)
    if (
        not missing_set
        or len(names) != len(missing_set)
        or len(exact_names) != len(exact_set)
        or missing_set & exact_set
        or missing_set | exact_set != expected
        or (state == "absent" and exact_set)
        or (state == "partial" and not exact_set)
    ):
        raise ReleaseStateError("PyPI plan selects an invalid missing subject set")
    sources: dict[str, Path] = {}
    for name in sorted(names):
        subject = manifest.subjects[name]
        source = directory / name
        value = _regular_bytes(source, expected_size=subject.size)
        if _sha256_bytes(value) != subject.sha256:
            raise ReleaseStateError(f"cannot stage a mismatched PyPI subject: {name}")
        sources[name] = source
    _empty_output_directory(output)
    try:
        for name, source in sources.items():
            shutil.copy2(source, output / name)
    except OSError as exc:
        raise ReleaseStateError(f"cannot stage PyPI subject: {exc}") from exc


def _write_json(path: Path, value: Any) -> None:
    _atomic_write(path, _canonical_json(value))


def stage_npm_signature_consumer(directory: Path, output: Path) -> None:
    """Retarget the frozen local-tarball lock to the identical registry tarball."""
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    subject = manifest.one("npm")
    tarball = _regular_bytes(directory / subject.name, expected_size=subject.size)
    if _sha256_bytes(tarball) != subject.sha256:
        raise ReleaseStateError("npm subject differs from the release manifest")
    bundle = directory / "npm-consumer"
    package = _require_object(_read_json(bundle / "package.json"), "npm consumer package")
    lock = _require_object(_read_json(bundle / "package-lock.json"), "npm consumer lock")
    package_copy = copy.deepcopy(package)
    lock_copy = copy.deepcopy(lock)
    local_spec = f"file:../{subject.name}"
    dependencies = package_copy.get("dependencies")
    if not isinstance(dependencies, dict) or dependencies.get(PACKAGE_NAME) != local_spec:
        raise ReleaseStateError("frozen npm consumer does not select the local subject")
    dependencies[PACKAGE_NAME] = manifest.coordinates.npm_version
    packages = lock_copy.get("packages")
    if not isinstance(packages, dict):
        raise ReleaseStateError("frozen npm consumer lock has no packages object")
    root = packages.get("")
    local = packages.get(f"node_modules/{PACKAGE_NAME}")
    if not isinstance(root, dict) or not isinstance(local, dict):
        raise ReleaseStateError("frozen npm consumer lock omits required entries")
    root_dependencies = root.get("dependencies")
    if not isinstance(root_dependencies, dict) or root_dependencies.get(PACKAGE_NAME) != local_spec:
        raise ReleaseStateError("frozen npm consumer lock root differs from its package")
    expected_integrity = _sha512_integrity(tarball)
    if (
        local.get("resolved") != local_spec
        or local.get("version") != manifest.coordinates.npm_version
        or local.get("integrity") != expected_integrity
    ):
        raise ReleaseStateError("frozen npm subject lock entry differs from candidate bytes")
    root_dependencies[PACKAGE_NAME] = manifest.coordinates.npm_version
    local["resolved"] = _npm_tarball_url(subject)
    _empty_output_directory(output)
    _write_json(output / "package.json", package_copy)
    _write_json(output / "package-lock.json", lock_copy)


def _retry(
    operation: Callable[[], Decision],
    *,
    required_state: str | None,
    required_release: str | None = None,
    attempts: int,
    delay: float,
    after_complete: Callable[[], None] | None = None,
) -> Decision:
    if attempts < 1 or attempts > MAX_ATTEMPTS:
        raise ReleaseStateError(f"attempts must be between 1 and {MAX_ATTEMPTS}")
    if not math.isfinite(delay) or delay < 0 or delay > MAX_RETRY_DELAY_SECONDS:
        raise ReleaseStateError(
            f"retry delay must be finite and between 0 and {MAX_RETRY_DELAY_SECONDS:g} seconds"
        )
    last_error: ReleaseStateError | None = None
    last_decision: Decision | None = None
    for attempt in range(attempts):
        try:
            candidate = operation()
            if (required_state is None or candidate.state == required_state) and (
                required_release is None or candidate.release == required_release
            ):
                if after_complete is not None:
                    after_complete()
                return candidate
            last_decision = candidate
        except NetworkStateError as exc:
            last_error = exc
            last_decision = None
        if attempt + 1 < attempts:
            time.sleep(delay)
    if last_decision is not None:
        return last_decision
    if last_error is not None:
        raise last_error
    raise AssertionError("retry loop produced neither a decision nor an error")


def _print_decision(decision: Decision) -> None:
    print(_canonical_json(decision.to_dict()).decode(), end="")


def _plan_exit(decision: Decision, required_state: str | None, require_published: bool) -> int:
    if decision.state in {"conflict", "unexpected"}:
        return 1
    if required_state is not None and decision.state != required_state:
        return 1
    if require_published and decision.release != "published":
        return 1
    return 0


def _add_retry_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--delay", type=float, default=DEFAULT_RETRY_DELAY_SECONDS)
    parser.add_argument("--require-state")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    controls = commands.add_parser("controls", help="generate non-cyclic release controls")
    controls.add_argument("directory", type=Path)

    recovery = commands.add_parser(
        "recovery-bundle",
        help="archive the exact frozen transfer for durable release recovery",
    )
    recovery.add_argument("directory", type=Path)
    recovery.add_argument("output", type=Path)

    extract = commands.add_parser(
        "extract-recovery",
        help="restore and verify a durable frozen transfer",
    )
    extract.add_argument("bundle", type=Path)
    extract.add_argument("output", type=Path)

    pypi = commands.add_parser("pypi-plan", help="classify exact PyPI file state")
    pypi.add_argument("directory", type=Path)
    pypi.add_argument("--fixture", type=Path)
    pypi.add_argument("--integrity-fixtures", type=Path)
    pypi.add_argument("--require-publisher-metadata", action="store_true")
    _add_retry_arguments(pypi)

    npm = commands.add_parser("npm-plan", help="classify exact npm version state")
    npm.add_argument("directory", type=Path)
    npm.add_argument("--fixture", type=Path)
    npm.add_argument("--tarball-fixture", type=Path)
    npm.add_argument("--packument-fixture", type=Path)
    npm.add_argument("--require-channel", action="store_true")
    _add_retry_arguments(npm)

    github = commands.add_parser("github-plan", help="classify GitHub release assets")
    github.add_argument("directory", type=Path)
    github.add_argument("--repo", required=True)
    github.add_argument("--tag", required=True)
    github.add_argument("--fixture", type=Path)
    github.add_argument("--asset-fixtures", type=Path)
    github.add_argument("--recovery-directory", type=Path)
    github.add_argument("--latest-fixture", type=Path)
    github.add_argument("--token-env", default="GITHUB_TOKEN")
    github.add_argument("--require-published", action="store_true")
    github.add_argument("--require-latest", action="store_true")
    _add_retry_arguments(github)

    stage_python = commands.add_parser("stage-pypi", help="stage only missing PyPI files")
    stage_python.add_argument("directory", type=Path)
    stage_python.add_argument("plan", type=Path)
    stage_python.add_argument("output", type=Path)

    stage_npm = commands.add_parser(
        "stage-npm-signature-consumer",
        help="retarget the frozen npm consumer to the exact registry tarball",
    )
    stage_npm.add_argument("directory", type=Path)
    stage_npm.add_argument("output", type=Path)

    check_npm = commands.add_parser(
        "check-npm-audit",
        help="enforce package and source identity on npm's verified attestation report",
    )
    check_npm.add_argument("directory", type=Path)
    check_npm.add_argument("report", type=Path)
    return parser


def _pypi_command(args: argparse.Namespace, directory: Path, manifest: Manifest) -> int:
    if args.require_publisher_metadata and args.require_state != "complete":
        raise ReleaseStateError("--require-publisher-metadata requires --require-state complete")

    def operation() -> Decision:
        return classify_pypi(manifest, _pypi_payload(manifest, args.fixture))

    def publisher_metadata() -> None:
        if args.require_publisher_metadata:
            try:
                check_pypi_integrity_metadata(
                    manifest,
                    _pypi_provenance_payloads(manifest, args.integrity_fixtures),
                )
            except ReleaseStateError as exc:
                raise NetworkStateError(str(exc)) from exc

    decision = _retry(
        operation,
        required_state=args.require_state,
        attempts=args.attempts,
        delay=args.delay,
        after_complete=publisher_metadata if args.require_publisher_metadata else None,
    )
    _print_decision(decision)
    return _plan_exit(decision, args.require_state, False)


def _npm_command(args: argparse.Namespace, directory: Path, manifest: Manifest) -> int:
    def operation() -> Decision:
        payload, tarball, packument = _npm_payloads(
            manifest,
            args.fixture,
            args.tarball_fixture,
            args.packument_fixture,
            require_channel=args.require_channel,
        )
        return classify_npm(
            manifest,
            payload,
            tarball,
            packument=packument,
            require_channel=args.require_channel,
        )

    decision = _retry(
        operation,
        required_state=args.require_state,
        attempts=args.attempts,
        delay=args.delay,
    )
    _print_decision(decision)
    return _plan_exit(decision, args.require_state, False)


def _github_command(args: argparse.Namespace, directory: Path, manifest: Manifest) -> int:
    if args.require_latest and not args.require_published:
        raise ReleaseStateError("--require-latest requires --require-published")
    recovery_directory = (
        args.recovery_directory.resolve() if args.recovery_directory is not None else None
    )
    expected = expected_github_assets(directory, manifest, recovery_directory)
    token = os.environ.get(args.token_env)

    def operation() -> Decision:
        payload, fallback = _github_payloads(
            manifest,
            expected,
            args.repo,
            args.tag,
            args.fixture,
            args.asset_fixtures,
            token,
        )
        return classify_github(manifest, expected, payload, fallback)

    def latest_postcondition() -> None:
        problems = classify_github_latest(
            manifest,
            _github_latest_payload(args.repo, args.latest_fixture, token),
        )
        if problems:
            summary = ", ".join(problem.code for problem in problems)
            raise NetworkStateError(f"GitHub latest-release postcondition failed: {summary}")

    decision = _retry(
        operation,
        required_state=args.require_state,
        required_release="published" if args.require_published else None,
        attempts=args.attempts,
        delay=args.delay,
        after_complete=latest_postcondition if args.require_latest else None,
    )
    _print_decision(decision)
    return _plan_exit(decision, args.require_state, args.require_published)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "extract-recovery":
            result = extract_recovery_bundle(args.bundle, args.output)
            print(_canonical_json(result).decode(), end="")
            return 0
        directory = args.directory.resolve()
        if args.command == "controls":
            print(_canonical_json(write_controls(directory)).decode(), end="")
            return 0
        if args.command == "recovery-bundle":
            result = write_recovery_bundle(directory, args.output)
            print(_canonical_json(result).decode(), end="")
            return 0
        if args.command == "stage-pypi":
            stage_pypi(directory, args.plan.resolve(), args.output.resolve())
            return 0
        if args.command == "stage-npm-signature-consumer":
            stage_npm_signature_consumer(directory, args.output.resolve())
            return 0
        manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
        if args.command == "check-npm-audit":
            check_npm_audit_attestations(directory, manifest, _read_json(args.report.resolve()))
            return 0
        if args.command == "pypi-plan":
            return _pypi_command(args, directory, manifest)
        if args.command == "npm-plan":
            return _npm_command(args, directory, manifest)
        if args.command == "github-plan":
            return _github_command(args, directory, manifest)
        raise AssertionError(f"unhandled command: {args.command}")
    except ReleaseStateError as exc:
        print(f"release-state: error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("release-state: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
