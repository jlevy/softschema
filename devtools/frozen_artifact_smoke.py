"""Build, freeze, transfer, and smoke one exact cross-platform artifact candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

CHECKSUM_NAME = "SHA256SUMS"
CHECKSUM_LINE = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")
MAX_CHECKSUM_BYTES = 4 * 1024 * 1024
HASH_CHUNK_BYTES = 1024 * 1024
MAX_CANDIDATE_FILE_BYTES = 512 * 1024 * 1024
MAX_CANDIDATE_TOTAL_BYTES = 1024 * 1024 * 1024
# A valid inventory line needs a 64-byte digest, two separators, a one-byte
# relative path, and a newline. Bound every traversed node (files and directories)
# by the maximum number of such lines that the checksum-file budget can represent.
MIN_CHECKSUM_LINE_BYTES = 64 + 2 + 1 + 1
MAX_CANDIDATE_NODES = MAX_CHECKSUM_BYTES // MIN_CHECKSUM_LINE_BYTES
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


def _load_candidate_helpers():
    """Import candidate-local build/smoke helpers only after verification when required."""
    # A transferred driver is executed by path, so its candidate root is not otherwise on
    # sys.path. Add exactly that parent and suppress bytecode writes while helpers load.
    # The verify-only path never calls this function; smoke calls it only after every
    # candidate byte has authenticated successfully.
    candidate_root = str(Path(__file__).resolve().parents[1])
    if candidate_root not in sys.path:
        sys.path.insert(0, candidate_root)
    previous_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        from devtools import installed_artifact_smoke as artifact_smoke
        from devtools.npm_consumer import create_consumer_bundle
    finally:
        sys.dont_write_bytecode = previous_dont_write_bytecode
    return artifact_smoke, create_consumer_bundle


@dataclass(frozen=True)
class _FileSnapshot:
    """Regular-file identity and mutation-sensitive metadata."""

    device: int
    inode: int
    size: int
    modified_ns: int
    changed_ns: int

    @classmethod
    def from_stat(cls, value: os.stat_result) -> _FileSnapshot:
        return cls(
            device=value.st_dev,
            inode=value.st_ino,
            size=value.st_size,
            modified_ns=value.st_mtime_ns,
            changed_ns=value.st_ctime_ns,
        )


def _sha256(directory: Path, name: str) -> tuple[str, _FileSnapshot]:
    digest = hashlib.sha256()
    descriptor = _open_regular_descriptor(
        directory,
        name,
        "candidate checksum subject is not regular",
    )
    try:
        before = _FileSnapshot.from_stat(os.fstat(descriptor))
        if before.size > MAX_CANDIDATE_FILE_BYTES:
            raise CandidateError(f"candidate file exceeds the byte limit: {name}")
        remaining = before.size + 1
        total = 0
        while remaining > 0:
            chunk = os.read(descriptor, min(HASH_CHUNK_BYTES, remaining))
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
            remaining -= len(chunk)
        after = _FileSnapshot.from_stat(os.fstat(descriptor))
    finally:
        os.close(descriptor)
    if after != before or total != before.size:
        raise CandidateError(f"candidate changed while hashing: {name}")
    return digest.hexdigest(), after


def _read_checksum_text(directory: Path) -> tuple[str, _FileSnapshot]:
    descriptor = _open_regular_descriptor(
        directory,
        CHECKSUM_NAME,
        "candidate has no regular SHA256SUMS file",
    )
    try:
        before = _FileSnapshot.from_stat(os.fstat(descriptor))
        chunks: list[bytes] = []
        total = 0
        limit = MAX_CHECKSUM_BYTES + 1
        while total < limit:
            chunk = os.read(descriptor, min(HASH_CHUNK_BYTES, limit - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        encoded = b"".join(chunks)
        after = _FileSnapshot.from_stat(os.fstat(descriptor))
    finally:
        os.close(descriptor)
    if len(encoded) > MAX_CHECKSUM_BYTES:
        raise CandidateError("candidate checksum inventory is oversized")
    if after != before or len(encoded) != before.size:
        raise CandidateError("candidate checksum inventory changed while reading")
    try:
        return encoded.decode("utf-8", errors="strict"), after
    except UnicodeDecodeError as exc:
        raise CandidateError("candidate checksum inventory is not UTF-8") from exc


def _regular_snapshot(directory: Path, name: str, message: str) -> _FileSnapshot:
    descriptor = _open_regular_descriptor(directory, name, message)
    try:
        return _FileSnapshot.from_stat(os.fstat(descriptor))
    finally:
        os.close(descriptor)


def _regular_file_flags() -> int:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    return flags


def _is_redirect(source_stat: os.stat_result) -> bool:
    """Return whether an lstat result can redirect traversal on this platform."""
    # On Windows, directory junctions are reparse points but are not reported as
    # POSIX symlinks. st_reparse_tag is available on Python 3.8+, including the
    # project's Python 3.11 floor. Reject every nonzero reparse tag conservatively.
    return stat.S_ISLNK(source_stat.st_mode) or bool(getattr(source_stat, "st_reparse_tag", 0))


def _same_identity(first: os.stat_result, second: os.stat_result) -> bool:
    return (
        first.st_ino != 0
        and second.st_ino != 0
        and (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)
    )


def _check_opened_identity(
    descriptor: int,
    source_stat: os.stat_result,
    message: str,
) -> None:
    opened_stat = os.fstat(descriptor)
    if _is_redirect(opened_stat) or not stat.S_ISREG(opened_stat.st_mode):
        raise CandidateError(message)
    if not _same_identity(opened_stat, source_stat):
        raise CandidateError(f"{message}: file identity changed")


def _open_regular_descriptor(directory: Path, name: str, message: str) -> int:
    normalized = _safe_checksum_path(name)
    parts = PurePosixPath(normalized).parts
    try:
        source_root_stat = directory.lstat()
        if _is_redirect(source_root_stat) or not stat.S_ISDIR(source_root_stat.st_mode):
            raise CandidateError(message)
        root = directory.resolve(strict=True)
        root_stat = root.lstat()
    except OSError as exc:
        raise CandidateError(message) from exc
    if (
        _is_redirect(root_stat)
        or not stat.S_ISDIR(root_stat.st_mode)
        or not _same_identity(source_root_stat, root_stat)
    ):
        raise CandidateError(message)

    supports_openat = (
        os.open in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
        and os.stat in os.supports_follow_symlinks
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
    )
    if supports_openat:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory_descriptor: int | None = None
        try:
            directory_descriptor = os.open(root, directory_flags)
            opened_root = os.fstat(directory_descriptor)
            if (
                _is_redirect(opened_root)
                or not stat.S_ISDIR(opened_root.st_mode)
                or not _same_identity(root_stat, opened_root)
            ):
                raise CandidateError(message)
            for component in parts[:-1]:
                child_descriptor = os.open(
                    component,
                    directory_flags,
                    dir_fd=directory_descriptor,
                )
                os.close(directory_descriptor)
                directory_descriptor = child_descriptor
            source_stat = os.stat(
                parts[-1],
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            if _is_redirect(source_stat) or not stat.S_ISREG(source_stat.st_mode):
                raise CandidateError(message)
            descriptor = os.open(
                parts[-1],
                _regular_file_flags(),
                dir_fd=directory_descriptor,
            )
            try:
                _check_opened_identity(descriptor, source_stat, message)
            except BaseException:
                os.close(descriptor)
                raise
            return descriptor
        except CandidateError:
            raise
        except OSError as exc:
            raise CandidateError(message) from exc
        finally:
            if directory_descriptor is not None:
                os.close(directory_descriptor)

    path = root.joinpath(*parts)
    checked_parents: list[tuple[Path, os.stat_result]] = []
    try:
        current = root
        current_root_stat = current.lstat()
        if (
            _is_redirect(current_root_stat)
            or not stat.S_ISDIR(current_root_stat.st_mode)
            or not _same_identity(current_root_stat, root_stat)
        ):
            raise CandidateError(message)
        checked_parents.append((current, current_root_stat))
        for component in parts[:-1]:
            current /= component
            component_stat = current.lstat()
            if _is_redirect(component_stat) or not stat.S_ISDIR(component_stat.st_mode):
                raise CandidateError(message)
            checked_parents.append((current, component_stat))
        source_stat = path.lstat()
    except OSError as exc:
        raise CandidateError(message) from exc
    if _is_redirect(source_stat) or not stat.S_ISREG(source_stat.st_mode):
        raise CandidateError(message)
    try:
        descriptor = os.open(path, _regular_file_flags())
    except OSError as exc:
        raise CandidateError(message) from exc
    try:
        _check_opened_identity(descriptor, source_stat, message)
        for parent, expected_parent_stat in checked_parents:
            current_parent_stat = parent.lstat()
            if (
                _is_redirect(current_parent_stat)
                or not stat.S_ISDIR(current_parent_stat.st_mode)
                or not _same_identity(current_parent_stat, expected_parent_stat)
            ):
                raise CandidateError(f"{message}: parent identity changed")
        final_stat = path.lstat()
        if (
            _is_redirect(final_stat)
            or not stat.S_ISREG(final_stat.st_mode)
            or not _same_identity(final_stat, source_stat)
        ):
            raise CandidateError(f"{message}: file identity changed")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _candidate_files(
    directory: Path,
    *,
    expected_names: set[str] | None = None,
    max_nodes: int | None = None,
) -> dict[str, _FileSnapshot]:
    try:
        source_root_stat = directory.lstat()
    except OSError as exc:
        raise CandidateError(f"candidate must be a directory: {directory}") from exc
    if _is_redirect(source_root_stat) or not stat.S_ISDIR(source_root_stat.st_mode):
        raise CandidateError(f"candidate must be a directory: {directory}")

    try:
        root = directory.resolve(strict=True)
        root_stat = root.lstat()
    except OSError as exc:
        raise CandidateError(f"candidate must be a directory: {directory}") from exc
    if (
        _is_redirect(root_stat)
        or not stat.S_ISDIR(root_stat.st_mode)
        or not _same_identity(source_root_stat, root_stat)
    ):
        raise CandidateError(f"candidate must be a directory: {directory}")

    node_limit = MAX_CANDIDATE_NODES if max_nodes is None else max_nodes
    node_count = 0
    total_bytes = 0
    result: dict[str, _FileSnapshot] = {}
    directory_order: list[str] = []
    directory_parent: dict[str, str] = {}
    directories_with_subjects: set[str] = set()
    pending = [(root, root_stat, "")]
    while pending:
        current, expected_directory_stat, current_relative = pending.pop()
        try:
            current_stat = current.lstat()
            if (
                _is_redirect(current_stat)
                or not stat.S_ISDIR(current_stat.st_mode)
                or not _same_identity(current_stat, expected_directory_stat)
            ):
                raise CandidateError(
                    f"candidate directory identity changed during inspection: {current}"
                )
            entries = os.scandir(current)
        except OSError as exc:
            raise CandidateError(f"candidate directory cannot be inspected: {current}") from exc
        with entries:
            for entry in entries:
                node_count += 1
                if node_count > node_limit:
                    raise CandidateError(f"candidate inventory exceeds the {node_limit}-node limit")
                if entry.name.startswith("."):
                    raise CandidateError(f"candidate contains a hidden node: {entry.path}")
                path = Path(entry.path)
                try:
                    # Python 3.11 reports zero device/inode fields from DirEntry.stat()
                    # on Windows. A fresh path lstat supplies the file index required
                    # for the descriptor identity check and avoids cached entry data.
                    source_stat = path.lstat()
                except OSError as exc:
                    raise CandidateError(f"candidate node cannot be inspected: {path}") from exc
                if _is_redirect(source_stat):
                    raise CandidateError(f"candidate contains a redirect: {path}")
                relative = path.relative_to(root).as_posix()
                if stat.S_ISDIR(source_stat.st_mode):
                    directory_order.append(relative)
                    directory_parent[relative] = current_relative
                    pending.append((path, source_stat, relative))
                    continue
                if not stat.S_ISREG(source_stat.st_mode):
                    raise CandidateError(f"candidate contains a non-regular node: {path}")
                if relative == CHECKSUM_NAME:
                    continue
                if source_stat.st_size > MAX_CANDIDATE_FILE_BYTES:
                    raise CandidateError(f"candidate file exceeds the byte limit: {relative}")
                total_bytes += source_stat.st_size
                if total_bytes > MAX_CANDIDATE_TOTAL_BYTES:
                    raise CandidateError("candidate aggregate exceeds the byte limit")
                if expected_names is not None and relative not in expected_names:
                    raise CandidateError(
                        f"candidate checksum inventory mismatch: missing=[], extra={[relative]}"
                    )
                result[relative] = _FileSnapshot.from_stat(source_stat)
                directories_with_subjects.add(current_relative)
        try:
            final_current_stat = current.lstat()
        except OSError as exc:
            raise CandidateError(
                f"candidate directory changed during inspection: {current}"
            ) from exc
        if (
            _is_redirect(final_current_stat)
            or not stat.S_ISDIR(final_current_stat.st_mode)
            or not _same_identity(final_current_stat, expected_directory_stat)
        ):
            raise CandidateError(
                f"candidate directory identity changed during inspection: {current}"
            )
    # Propagate descendant-file state once in reverse discovery order. This detects
    # empty/unexplained directories in O(nodes), without expanding every file's parent
    # chain independently.
    for relative in reversed(directory_order):
        if relative in directories_with_subjects:
            directories_with_subjects.add(directory_parent[relative])
    unexpected_directories = set(directory_order) - directories_with_subjects
    if unexpected_directories:
        raise CandidateError(
            f"candidate contains unexpected directories: {sorted(unexpected_directories)}"
        )
    return result


def write_transfer_checksums(directory: Path) -> Path:
    """Write a deterministic recursive SHA-256 inventory after candidate assembly."""
    files = _candidate_files(directory)
    if not files:
        raise CandidateError("candidate contains no files")
    output = directory / CHECKSUM_NAME
    lines: list[str] = []
    encoded_bytes = 0
    for name in sorted(files):
        digest, snapshot = _sha256(directory, name)
        if snapshot != files[name]:
            raise CandidateError(f"candidate changed before checksums were written: {name}")
        line = f"{digest}  {name}\n"
        encoded_bytes += len(line.encode("utf-8"))
        if encoded_bytes > MAX_CHECKSUM_BYTES:
            raise CandidateError("generated checksum inventory is oversized")
        lines.append(line)
    text = "".join(lines)
    temporary = output.with_name(f".{output.name}.tmp")
    # Preserve the exact LF bytes charged above. Text-mode writes translate newlines
    # on Windows and could otherwise exceed the shared ceiling after the size check.
    temporary.write_bytes(text.encode("utf-8"))
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
    expected: dict[str, str] = {}
    checksum_text, checksum_snapshot = _read_checksum_text(directory)
    for line in checksum_text.splitlines():
        match = CHECKSUM_LINE.fullmatch(line)
        if match is None:
            raise CandidateError(f"invalid checksum line: {line!r}")
        name = _safe_checksum_path(match.group(2))
        if name in expected:
            raise CandidateError(f"duplicate checksum path: {name!r}")
        expected[name] = match.group(1)
    if not expected:
        raise CandidateError("candidate checksum inventory is empty")
    actual = _candidate_files(directory, expected_names=set(expected))
    if set(expected) != set(actual):
        raise CandidateError(
            "candidate checksum inventory mismatch: "
            f"missing={sorted(set(expected) - set(actual))}, "
            f"extra={sorted(set(actual) - set(expected))}"
        )
    for name in sorted(expected):
        digest = expected[name]
        actual_digest, hashed_snapshot = _sha256(directory, name)
        if actual_digest != digest:
            raise CandidateError(
                f"candidate digest mismatch for {name}: expected {digest}, got {actual_digest}"
            )
        if hashed_snapshot != actual[name]:
            raise CandidateError(f"candidate changed before it could be verified: {name}")
    final_actual = _candidate_files(directory, expected_names=set(expected))
    if final_actual != actual:
        raise CandidateError("candidate checksum inventory changed during verification")
    final_checksum_snapshot = _regular_snapshot(
        directory,
        CHECKSUM_NAME,
        "candidate has no regular SHA256SUMS file",
    )
    if final_checksum_snapshot != checksum_snapshot:
        raise CandidateError("candidate checksum inventory changed during verification")


def stage_smoke_support(directory: Path) -> None:
    """Copy only the source references and drivers required by downstream smoke."""
    artifact_smoke, _create_consumer_bundle = _load_candidate_helpers()
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
    artifact_smoke, create_consumer_bundle = _load_candidate_helpers()
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
    artifact_smoke, _create_consumer_bundle = _load_candidate_helpers()
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
    # Preserve the final path component so verification can reject a redirected
    # candidate root. ``absolute`` normalizes the invocation location without
    # dereferencing a POSIX link or Windows junction as ``resolve`` would.
    directory = args.directory.absolute()
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
