"""Build and verify immutable softschema release inputs and artifacts.

This module is deliberately usable as both a library in tests and a small release
driver in GitHub Actions.  It does not publish anything and never reads registry state.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import tarfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from jsonschema import Draft202012Validator

from conformance.run import Corpus, load_corpus

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
TAG_PATTERN = re.compile(
    r"^v(?P<major>0|[1-9][0-9]*)\."
    r"(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)"
    r"(?:-rc\.(?P<rc>[1-9][0-9]*))?$"
)

SubjectKind = Literal[
    "wheel",
    "sdist",
    "npm",
    "conformance",
    "release_metadata",
    "build_metadata",
    "sbom",
]

MEDIA_TYPES: dict[SubjectKind, str] = {
    "wheel": "application/zip",
    "sdist": "application/gzip",
    "npm": "application/gzip",
    "conformance": "application/gzip",
    "release_metadata": "application/json",
    "build_metadata": "application/json",
    "sbom": "application/spdx+json",
}


class ReleaseError(RuntimeError):
    """A deterministic release policy or artifact-integrity failure."""


@dataclass(frozen=True)
class ReleaseCoordinates:
    """One logical tag mapped to each package ecosystem."""

    logical_version: str
    python_version: str
    npm_version: str
    npm_tag: Literal["latest", "next"]
    prerelease: bool


@dataclass(frozen=True)
class ReleaseSubject:
    """A primary immutable release subject included in the external manifest."""

    kind: SubjectKind
    path: Path


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _strict_json(path: Path) -> Any:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ReleaseError(f"{path}: duplicate JSON key {key!r}")
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ReleaseError(f"{path}: non-finite JSON number {value}")

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"cannot read strict JSON from {path}: {exc}") from exc


def _validate(value: Any, schema_name: str, corpus: Corpus) -> None:
    validator = Draft202012Validator(corpus.schemas[schema_name], registry=corpus.registry)
    errors = sorted(
        validator.iter_errors(value),
        key=lambda error: ([str(part) for part in error.absolute_path], error.message),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise ReleaseError(f"{schema_name} validation failed at {location}: {first.message}")


def release_coordinates(tag: str) -> ReleaseCoordinates:
    """Map the only supported stable/RC tag shapes to Python and npm versions."""
    match = TAG_PATTERN.fullmatch(tag)
    if match is None:
        raise ReleaseError(f"unsupported release tag {tag!r}; expected vX.Y.Z or vX.Y.Z-rc.N")
    base = ".".join(match.group(name) for name in ("major", "minor", "patch"))
    rc = match.group("rc")
    if rc is None:
        return ReleaseCoordinates(base, base, base, "latest", False)
    logical = f"{base}-rc.{rc}"
    return ReleaseCoordinates(logical, f"{base}rc{rc}", logical, "next", True)


def _expected_subject_kinds(coordinates: ReleaseCoordinates) -> dict[str, SubjectKind]:
    return {
        f"softschema-{coordinates.python_version}-py3-none-any.whl": "wheel",
        f"softschema-{coordinates.python_version}.tar.gz": "sdist",
        f"softschema-{coordinates.npm_version}.tgz": "npm",
        "conformance-kit.tar.gz": "conformance",
        "release-metadata.json": "release_metadata",
        "build-metadata.json": "build_metadata",
        "softschema-python-wheel.spdx.json": "sbom",
        "softschema-python-sdist.spdx.json": "sbom",
        "softschema-npm.spdx.json": "sbom",
    }


def _release_order(logical_version: str) -> tuple[int, int, int, int, int]:
    match = TAG_PATTERN.fullmatch(f"v{logical_version}")
    if match is None:  # release_coordinates owns the public error message
        raise ReleaseError(f"invalid logical version: {logical_version!r}")
    major, minor, patch = (int(match.group(name)) for name in ("major", "minor", "patch"))
    rc = match.group("rc")
    return (major, minor, patch, 1 if rc is None else 0, 0 if rc is None else int(rc))


def _validate_package_coordinates(metadata: dict[str, Any]) -> None:
    """Validate build versions separately from last registry-verified bootstrap pins."""
    coordinates = release_coordinates(f"v{metadata['logical_version']}")
    packages = metadata["packages"]
    expected_versions = {
        "python": coordinates.python_version,
        "npm": coordinates.npm_version,
    }
    for ecosystem, expected in expected_versions.items():
        package = packages[ecosystem]
        if package["version"] != expected:
            raise ReleaseError(
                f"{ecosystem} version {package['version']!r} does not map from "
                f"logical version {coordinates.logical_version!r}"
            )

    try:
        pinned = release_coordinates(f"v{packages['npm']['pin']}")
    except ReleaseError as exc:
        raise ReleaseError("npm bootstrap pin must be a stable logical version") from exc
    if pinned.prerelease:
        raise ReleaseError("bootstrap pins must identify a stable verified release")
    if packages["python"]["pin"] != pinned.python_version:
        raise ReleaseError("Python and npm bootstrap pins must map to the same release")
    if _release_order(pinned.logical_version) > _release_order(coordinates.logical_version):
        raise ReleaseError("bootstrap pins cannot be newer than the source release")
    state = metadata["release_state"]
    if state == "candidate" and pinned.logical_version == coordinates.logical_version:
        raise ReleaseError("candidate bootstrap pins must remain on the prior verified release")
    if (
        state == "released"
        and not coordinates.prerelease
        and pinned.logical_version != coordinates.logical_version
    ):
        raise ReleaseError("released bootstrap pins must identify the verified release")


def load_and_validate_metadata(root: Path) -> dict[str, Any]:
    """Load root logical metadata and enforce its cross-field release invariants."""
    metadata_path = root / "release-metadata.json"
    value = _strict_json(metadata_path)
    if not isinstance(value, dict):
        raise ReleaseError("release-metadata.json must contain an object")
    corpus = load_corpus()
    _validate(value, "release-metadata.schema.json", corpus)

    metadata = cast(dict[str, Any], value)
    coordinates = release_coordinates(f"v{metadata['logical_version']}")
    packages = metadata["packages"]
    _validate_package_coordinates(metadata)

    package_manifest_path = root / "packages" / "typescript" / "package.json"
    package_manifest = _strict_json(package_manifest_path)
    if not isinstance(package_manifest, dict):
        raise ReleaseError("packages/typescript/package.json must contain an object")
    npm_package = packages["npm"]
    if package_manifest.get("name") != npm_package["name"]:
        raise ReleaseError("npm package name differs from release metadata")
    if package_manifest.get("version") != npm_package["version"]:
        raise ReleaseError("npm package version differs from release metadata")

    try:
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ReleaseError(f"cannot read pyproject.toml: {exc}") from exc
    if pyproject.get("project", {}).get("name") != packages["python"]["name"]:
        raise ReleaseError("Python package name differs from release metadata")

    formats = metadata["artifact_formats"]
    if formats["current"] not in formats["supported"]:
        raise ReleaseError("current artifact format must be included in supported formats")
    if metadata["release_state"] != "development":
        if metadata["conformance"]["status"] == "unavailable":
            raise ReleaseError("candidate and released metadata must include the conformance kit")
        expected_artifacts = set(_expected_subject_kinds(coordinates))
        if set(metadata["expected_artifacts"]) != expected_artifacts:
            raise ReleaseError(
                "release metadata must name the exact primary artifact set: "
                f"{sorted(expected_artifacts)}"
            )
    return metadata


def _conformance_files(root: Path, corpus: Corpus) -> list[Path]:
    conformance = root / "conformance"
    if not conformance.is_dir():
        raise ReleaseError(f"missing conformance directory: {conformance}")
    files = {*corpus.archive_files, conformance / "manifest.lock.json"}

    for path in files:
        if path.is_symlink() or not path.is_file():
            raise ReleaseError(f"conformance closure contains an unsafe file: {path}")
    actual_case_files = {
        path
        for path in conformance.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
        and not path.name.startswith(".")
        and not any(part in {"agent-skills", "skill-installer"} for part in path.parts)
    }
    extra = actual_case_files - files
    if extra:
        names = sorted(path.relative_to(root).as_posix() for path in extra)
        raise ReleaseError(f"undeclared conformance files are not archived: {names}")
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def build_conformance_archive(
    root: Path,
    destination: Path,
    *,
    digest_output: Path | None = None,
) -> str:
    """Create a byte-reproducible gzip-compressed tar of the conformance kit."""
    corpus = load_corpus()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with (
        destination.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as zipped,
        tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive,
    ):
        for path in _conformance_files(root, corpus):
            relative = path.relative_to(root).as_posix()
            info = tarfile.TarInfo(relative)
            data = path.read_bytes()
            info.size = len(data)
            info.mode = 0o755 if path.name == "run.py" else 0o644
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, fileobj=_BytesReader(data))
    digest = _sha256_file(destination)
    if digest_output is not None:
        digest_output.parent.mkdir(parents=True, exist_ok=True)
        temporary = digest_output.with_name(f".{digest_output.name}.tmp")
        temporary.write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
        temporary.replace(digest_output)
    return digest


class _BytesReader:
    """Minimal binary reader accepted by ``TarFile.addfile``."""

    def __init__(self, value: bytes) -> None:
        self._value = value
        self._position = 0

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._value) - self._position
        result = self._value[self._position : self._position + size]
        self._position += len(result)
        return result


def build_metadata(
    root: Path,
    *,
    source_commit: str,
    conformance_archive: Path | None,
) -> dict[str, Any]:
    """Derive non-self-referential build identity from immutable inputs."""
    if COMMIT_PATTERN.fullmatch(source_commit) is None:
        raise ReleaseError("source commit must be 40 lowercase hexadecimal characters")
    load_and_validate_metadata(root)
    release_digest = _sha256_file(root / "release-metadata.json")
    identity: dict[str, str] = {
        "release_metadata_sha256": release_digest,
        "source_commit": source_commit,
    }
    if conformance_archive is not None:
        if not conformance_archive.is_file():
            raise ReleaseError(f"conformance archive does not exist: {conformance_archive}")
        identity["conformance_sha256"] = _sha256_file(conformance_archive)
    value: dict[str, Any] = {
        "schema_version": "1",
        **identity,
        "build_id": f"sha256:{_sha256_bytes(_canonical_json(identity))}",
    }
    _validate(value, "build-metadata.schema.json", load_corpus())
    return value


def build_release_manifest(
    *,
    logical_version: str,
    source_commit: str,
    subjects: list[ReleaseSubject],
) -> dict[str, Any]:
    """Build the external owner of exact primary artifact digests."""
    release_coordinates(f"v{logical_version}")
    if COMMIT_PATTERN.fullmatch(source_commit) is None:
        raise ReleaseError("source commit must be 40 lowercase hexadecimal characters")
    values: dict[str, Any] = {}
    for subject in subjects:
        path = subject.path
        name = path.name
        if path.is_symlink() or not path.is_file():
            raise ReleaseError(f"release subject must be a regular file: {path}")
        if name != str(path.relative_to(path.parent)) or SAFE_NAME_PATTERN.fullmatch(name) is None:
            raise ReleaseError(f"unsafe release subject name: {name!r}")
        if name in values:
            raise ReleaseError(f"duplicate release subject name: {name}")
        try:
            media_type = MEDIA_TYPES[subject.kind]
        except KeyError as exc:
            raise ReleaseError(f"unsupported release subject kind: {subject.kind}") from exc
        values[name] = {
            "kind": subject.kind,
            "media_type": media_type,
            "size": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
    manifest = {
        "schema_version": "1",
        "logical_version": logical_version,
        "source_commit": source_commit,
        "subjects": values,
    }
    _validate(manifest, "release-manifest.schema.json", load_corpus())
    return manifest


def verify_release_manifest(manifest: dict[str, Any], directory: Path) -> None:
    """Verify every declared subject against one flat immutable transfer directory."""
    _validate(manifest, "release-manifest.schema.json", load_corpus())
    expected_names = set(manifest["subjects"])
    actual_names = {
        path.name for path in directory.iterdir() if path.is_file() or path.is_symlink()
    }
    extra = actual_names - expected_names - {"release-manifest.json", "SHA256SUMS"}
    missing = expected_names - actual_names
    if extra or missing:
        raise ReleaseError(
            f"release subject inventory mismatch: missing={sorted(missing)}, extra={sorted(extra)}"
        )
    for name, expected in manifest["subjects"].items():
        path = directory / name
        if path.parent != directory or path.is_symlink() or not path.is_file():
            raise ReleaseError(f"missing or unsafe release subject: {name}")
        actual = _sha256_file(path)
        if actual != expected["sha256"]:
            raise ReleaseError(
                f"digest mismatch for {name}: expected {expected['sha256']}, got {actual}"
            )
        if path.stat().st_size != expected["size"]:
            raise ReleaseError(f"size mismatch for {name}")


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(_json_text(value), encoding="utf-8")
    temporary.replace(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="validate logical and build metadata")
    check.add_argument("--tag")

    archive = commands.add_parser("archive-conformance", help="build the deterministic kit")
    archive.add_argument("output", type=Path)
    archive.add_argument("--sha256-output", type=Path)

    build = commands.add_parser("build-metadata", help="derive and write build metadata")
    build.add_argument("output", type=Path)
    build.add_argument("--source-commit", required=True)
    build.add_argument("--conformance-archive", type=Path)

    coordinates = commands.add_parser("coordinates", help="map one release tag")
    coordinates.add_argument("tag")

    manifest = commands.add_parser("manifest", help="write an external release manifest")
    manifest.add_argument("output", type=Path)
    manifest.add_argument("--logical-version", required=True)
    manifest.add_argument("--source-commit", required=True)
    manifest.add_argument(
        "--subject",
        action="append",
        required=True,
        metavar="KIND=PATH",
        help="Primary subject kind and file; repeat for every immutable subject.",
    )

    verify = commands.add_parser("verify", help="verify a release manifest and directory")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("directory", type=Path)
    return parser


def _parse_subject(value: str) -> ReleaseSubject:
    kind_text, separator, path_text = value.partition("=")
    if separator == "" or not path_text:
        raise ReleaseError(f"subject must have KIND=PATH form: {value!r}")
    if kind_text not in MEDIA_TYPES:
        raise ReleaseError(f"unsupported release subject kind: {kind_text!r}")
    return ReleaseSubject(kind=kind_text, path=Path(path_text))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    if args.command == "check":
        metadata = load_and_validate_metadata(root)
        if args.tag is not None:
            actual = release_coordinates(args.tag)
            if actual.logical_version != metadata["logical_version"]:
                raise ReleaseError(
                    f"tag {args.tag} does not match logical version {metadata['logical_version']}"
                )
            if metadata["release_state"] != "candidate":
                raise ReleaseError("tag publication requires release_state 'candidate'")
        print(_json_text(metadata), end="")
        return 0
    if args.command == "archive-conformance":
        build_conformance_archive(root, args.output, digest_output=args.sha256_output)
        return 0
    if args.command == "build-metadata":
        value = build_metadata(
            root,
            source_commit=args.source_commit,
            conformance_archive=args.conformance_archive,
        )
        _write_json(args.output, value)
        return 0
    if args.command == "coordinates":
        print(_json_text(release_coordinates(args.tag).__dict__), end="")
        return 0
    if args.command == "manifest":
        value = build_release_manifest(
            logical_version=args.logical_version,
            source_commit=args.source_commit,
            subjects=[_parse_subject(subject) for subject in args.subject],
        )
        metadata = load_and_validate_metadata(root)
        expected = set(metadata["expected_artifacts"])
        actual = set(value["subjects"])
        if expected and expected != actual:
            raise ReleaseError(
                f"release metadata subject set differs: expected={sorted(expected)}, "
                f"actual={sorted(actual)}"
            )
        if expected:
            expected_kinds = _expected_subject_kinds(
                release_coordinates(f"v{metadata['logical_version']}")
            )
            actual_kinds = {
                name: cast(SubjectKind, subject["kind"])
                for name, subject in value["subjects"].items()
            }
            if actual_kinds != expected_kinds:
                raise ReleaseError("release subject kinds do not match their artifact names")
        _write_json(args.output, value)
        return 0
    if args.command == "verify":
        value = _strict_json(args.manifest)
        if not isinstance(value, dict):
            raise ReleaseError("release manifest must contain an object")
        verify_release_manifest(cast(dict[str, Any], value), args.directory.resolve())
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
