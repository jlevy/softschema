"""Build, freeze, transfer, and smoke one exact cross-platform artifact candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path, PurePosixPath

# A transferred driver is executed by path, so its candidate root is not otherwise on
# sys.path. Adding that one known parent keeps both source and transferred imports
# package-qualified and avoids accidental resolution from the consumer working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from devtools import installed_artifact_smoke as artifact_smoke
from devtools.npm_consumer import create_consumer_bundle

CHECKSUM_NAME = "SHA256SUMS"
CHECKSUM_LINE = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")
SMOKE_SUPPORT = (
    "release-metadata.json",
    "build-metadata.json",
    "devtools/installed_artifact_smoke.py",
    "devtools/__init__.py",
    "devtools/verify_installed_wheel.py",
    "devtools/npm_consumer.py",
    "devtools/frozen_artifact_smoke.py",
    "examples/movie_page/spirited-away.md",
    "examples/movie_page/spirited-away.yaml",
    "examples/movie_page/movie-page.schema.yaml",
    "docs/softschema-guide.md",
    "skills/softschema/SKILL.md",
)


class CandidateError(RuntimeError):
    """A candidate transfer or locked-consumer invariant failed."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate_files(directory: Path) -> dict[str, Path]:
    if directory.is_symlink() or not directory.is_dir():
        raise CandidateError(f"candidate must be a directory: {directory}")
    result: dict[str, Path] = {}
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise CandidateError(f"candidate contains a symlink: {path}")
        if not path.is_file() or path.name == CHECKSUM_NAME:
            continue
        relative = path.relative_to(directory).as_posix()
        result[relative] = path
    return result


def write_transfer_checksums(directory: Path) -> Path:
    """Write a deterministic recursive SHA-256 inventory after candidate assembly."""
    files = _candidate_files(directory)
    if not files:
        raise CandidateError("candidate contains no files")
    output = directory / CHECKSUM_NAME
    text = "".join(f"{_sha256(files[name])}  {name}\n" for name in sorted(files))
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(output)
    return output


def _safe_checksum_path(value: str) -> str:
    normalized = value[2:] if value.startswith("./") else value
    path = PurePosixPath(normalized)
    if (
        not normalized
        or "\\" in normalized
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
    ):
        raise CandidateError(f"unsafe checksum path: {value!r}")
    return path.as_posix()


def verify_transfer_checksums(directory: Path) -> None:
    """Verify every transferred file before any candidate dependency is installed."""
    checksum_path = directory / CHECKSUM_NAME
    if checksum_path.is_symlink() or not checksum_path.is_file():
        raise CandidateError("candidate has no regular SHA256SUMS file")
    expected: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        match = CHECKSUM_LINE.fullmatch(line)
        if match is None:
            raise CandidateError(f"invalid checksum line: {line!r}")
        name = _safe_checksum_path(match.group(2))
        if name in expected:
            raise CandidateError(f"duplicate checksum path: {name!r}")
        expected[name] = match.group(1)
    actual = _candidate_files(directory)
    if set(expected) != set(actual):
        raise CandidateError(
            "candidate checksum inventory mismatch: "
            f"missing={sorted(set(expected) - set(actual))}, "
            f"extra={sorted(set(actual) - set(expected))}"
        )
    for name, digest in expected.items():
        actual_digest = _sha256(actual[name])
        if actual_digest != digest:
            raise CandidateError(
                f"candidate digest mismatch for {name}: expected {digest}, got {actual_digest}"
            )


def stage_smoke_support(directory: Path) -> None:
    """Copy only the source references and drivers required by downstream smoke."""
    directory.mkdir(parents=True, exist_ok=True)
    for relative in SMOKE_SUPPORT:
        source = artifact_smoke.ROOT / relative
        if source.is_symlink() or not source.is_file():
            raise CandidateError(f"smoke support must be a regular file: {source}")
        destination = directory / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def build_candidate(
    directory: Path,
    *,
    cutoff: str,
    expected_npm_version: str,
) -> dict[str, str]:
    """Build once, create the locked consumer, and freeze the transfer inventory."""
    if directory.exists() and (
        directory.is_symlink() or not directory.is_dir() or any(directory.iterdir())
    ):
        raise CandidateError(f"candidate output must be absent or empty: {directory}")
    artifact_smoke._build(directory)
    stage_smoke_support(directory)
    npm = artifact_smoke._one(directory, "*.tgz")
    create_consumer_bundle(
        directory / "npm-consumer",
        npm,
        cutoff=cutoff,
        expected_npm_version=expected_npm_version,
    )
    write_transfer_checksums(directory)
    return {
        "npm": npm.name,
        "sdist": artifact_smoke._one(directory, "softschema-*.tar.gz").name,
        "wheel": artifact_smoke._one(directory, "*.whl").name,
    }


def smoke_candidate(directory: Path) -> dict[str, str]:
    """Verify checksums, then install and execute the exact candidate subjects."""
    verify_transfer_checksums(directory)
    return artifact_smoke.smoke(directory)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="build and freeze a candidate transfer")
    build.add_argument("directory", type=Path)
    build.add_argument("--cutoff", required=True)
    build.add_argument("--npm-version", required=True)

    stage = commands.add_parser("stage", help="copy downstream smoke support files")
    stage.add_argument("directory", type=Path)

    checksums = commands.add_parser("checksums", help="write recursive transfer checksums")
    checksums.add_argument("directory", type=Path)

    verify = commands.add_parser("verify-checksums", help="verify a candidate before install")
    verify.add_argument("directory", type=Path)

    smoke = commands.add_parser("smoke", help="verify and smoke an existing candidate")
    smoke.add_argument("directory", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    directory = args.directory.resolve()
    if args.command == "build":
        result = build_candidate(
            directory,
            cutoff=args.cutoff,
            expected_npm_version=args.npm_version,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.command == "stage":
        stage_smoke_support(directory)
        return 0
    if args.command == "checksums":
        write_transfer_checksums(directory)
        return 0
    if args.command == "verify-checksums":
        verify_transfer_checksums(directory)
        return 0
    if args.command == "smoke":
        print(json.dumps(smoke_candidate(directory), sort_keys=True))
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
