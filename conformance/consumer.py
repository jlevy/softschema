"""Verify an extracted conformance kit using only the Python standard library."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, cast

LOCK_FORMAT = "softschema-conformance-integrity-v1"
HASH_CHUNK_BYTES = 64 * 1024
MAX_INTEGRITY_LOCK_BYTES = 4 * 1024 * 1024
MAX_INTEGRITY_FILES = 4096
MAX_INTEGRITY_NODES = 16_384
MAX_INTEGRITY_PATH_DEPTH = 16
MAX_INTEGRITY_FILE_BYTES = 16 * 1024 * 1024
MAX_INTEGRITY_BUNDLE_BYTES = 64 * 1024 * 1024
MAX_JSON_DEPTH = 128
MAX_JSON_NODES = 100_000
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_LOCK_FIELDS = {"files", "format", "kit_version"}
_ENTRY_FIELDS = {"path", "sha256", "size"}


class ConsumerError(RuntimeError):
    """A standalone kit inventory or digest failure."""


def _strict_json(path: Path, *, root: Path) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ConsumerError(f"{path}: duplicate JSON key {key!r}")
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ConsumerError(f"{path}: non-finite JSON number {value}")

    def parse_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            reject_constant(value)
        return parsed

    try:
        root = root.resolve()
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
        if path.is_symlink() or not resolved.is_file():
            raise ConsumerError("integrity lock is not a regular confined file")
        size = resolved.stat().st_size
        if size > MAX_INTEGRITY_LOCK_BYTES:
            raise ConsumerError("integrity lock exceeds the byte limit")
        with resolved.open("rb") as stream:
            data = stream.read(MAX_INTEGRITY_LOCK_BYTES + 1)
        if len(data) != size:
            raise ConsumerError("integrity lock changed while reading")
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
            parse_float=parse_float,
        )
        _validate_json_structure(value)
        return value
    except ConsumerError:
        raise
    except (OSError, UnicodeError, RecursionError, ValueError) as exc:
        raise ConsumerError(f"cannot read integrity lock: {exc}") from exc


def _validate_json_structure(value: Any) -> None:
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise ConsumerError("integrity lock exceeds the depth limit")
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise ConsumerError("integrity lock exceeds the node limit")
        if isinstance(current, str):
            try:
                current.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise ConsumerError(
                    "integrity lock contains an invalid Unicode scalar value"
                ) from exc
        elif isinstance(current, dict):
            for key in current:
                try:
                    key.encode("utf-8", errors="strict")
                except UnicodeEncodeError as exc:
                    raise ConsumerError(
                        "integrity lock contains an invalid Unicode scalar key"
                    ) from exc
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)


def _integrity_parts(value: Any) -> tuple[str, tuple[str, ...]]:
    if not isinstance(value, str):
        raise ConsumerError(f"unsafe integrity path: {value!r}")
    parts = tuple(value.split("/"))
    if (
        "\\" in value
        or PurePosixPath(value).is_absolute()
        or len(parts) < 2
        or len(parts) > MAX_INTEGRITY_PATH_DEPTH
        or parts[0] != "conformance"
        or any(part in {"", ".", ".."} for part in parts)
        or PurePosixPath(value).as_posix() != value
    ):
        raise ConsumerError(f"unsafe integrity path: {value!r}")
    return value, parts


def _hash_file(path: Path, expected_size: int, relative: str) -> str:
    digest = hashlib.sha256()
    remaining = expected_size
    with path.open("rb") as stream:
        while remaining:
            chunk = stream.read(min(HASH_CHUNK_BYTES, remaining))
            if not chunk:
                raise ConsumerError(f"size mismatch: {relative}")
            digest.update(chunk)
            remaining -= len(chunk)
        if stream.read(1):
            raise ConsumerError(f"size mismatch: {relative}")
    return digest.hexdigest()


def verify(root: Path) -> dict[str, Any]:
    """Verify the lock inventory below an extracted archive root."""
    supplied_root = root
    try:
        if supplied_root.is_symlink():
            raise ConsumerError("archive root must not be a symlink")
        root = supplied_root.resolve(strict=True)
    except OSError as exc:
        raise ConsumerError(f"cannot resolve archive root: {exc}") from exc
    if not root.is_dir():
        raise ConsumerError("archive root is not a directory")
    conformance_path = root / "conformance"
    if conformance_path.is_symlink() or not conformance_path.is_dir():
        raise ConsumerError("missing or unsafe conformance directory")
    conformance_root = conformance_path.resolve()
    lock_path = conformance_path / "manifest.lock.json"
    lock = _strict_json(lock_path, root=conformance_root)
    if not isinstance(lock, dict):
        raise ConsumerError("unsupported or malformed integrity lock")
    lock_object = cast(dict[str, Any], lock)
    if (
        set(lock_object) != _LOCK_FIELDS
        or lock_object.get("format") != LOCK_FORMAT
        or not isinstance(lock_object.get("kit_version"), str)
        or not lock_object["kit_version"]
    ):
        raise ConsumerError("unsupported or malformed integrity lock")
    entries = lock_object.get("files")
    if not isinstance(entries, list) or not entries or len(entries) > MAX_INTEGRITY_FILES:
        raise ConsumerError("integrity lock has an invalid file count")

    declared: set[Path] = set()
    declared_bytes = 0
    previous = ""
    for raw_entry in cast(list[Any], entries):
        if not isinstance(raw_entry, dict):
            raise ConsumerError("integrity lock entry must be an object")
        entry = cast(dict[str, Any], raw_entry)
        if set(entry) != _ENTRY_FIELDS:
            raise ConsumerError("integrity lock entry must be an object")
        relative, parts = _integrity_parts(entry.get("path"))
        if relative <= previous:
            raise ConsumerError("integrity paths must be unique and sorted")
        previous = relative
        size = entry.get("size")
        if type(size) is not int or size < 0:
            raise ConsumerError(f"invalid integrity size: {relative}")
        if size > MAX_INTEGRITY_FILE_BYTES:
            raise ConsumerError(f"integrity file exceeds the byte limit: {relative}")
        declared_bytes += size
        if declared_bytes > MAX_INTEGRITY_BUNDLE_BYTES:
            raise ConsumerError("integrity inventory exceeds the aggregate byte limit")
        expected_digest = entry.get("sha256")
        if (
            not isinstance(expected_digest, str)
            or _SHA256_PATTERN.fullmatch(expected_digest) is None
        ):
            raise ConsumerError(f"invalid integrity digest: {relative}")
        path = root.joinpath(*parts)
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(conformance_root)
        except (OSError, ValueError) as exc:
            raise ConsumerError(
                f"integrity path is missing or escapes conformance root: {relative}"
            ) from exc
        if path.is_symlink() or not path.is_file():
            raise ConsumerError(f"missing or unsafe declared file: {relative}")
        if path.stat().st_size != size:
            raise ConsumerError(f"size mismatch: {relative}")
        if expected_digest != _hash_file(path, size, relative):
            raise ConsumerError(f"digest mismatch: {relative}")
        declared.add(path)

    allowed_files = declared | {lock_path}
    allowed_directories = {conformance_path}
    for path in allowed_files:
        parent = path.parent
        while parent != root:
            allowed_directories.add(parent)
            parent = parent.parent
    extras: list[str] = []
    unsafe: list[str] = []
    nodes = 0
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            with os.scandir(directory) as iterator:
                entries_in_directory: list[os.DirEntry[str]] = []
                for entry in iterator:
                    nodes += 1
                    if nodes > MAX_INTEGRITY_NODES:
                        raise ConsumerError("kit inventory exceeds the node limit")
                    entries_in_directory.append(entry)
                entries_in_directory.sort(key=lambda entry: entry.name)
        except OSError as exc:
            raise ConsumerError(f"cannot inspect kit inventory: {exc}") from exc
        for entry in entries_in_directory:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            try:
                if entry.is_symlink():
                    unsafe.append(relative)
                elif entry.is_file(follow_symlinks=False):
                    if path not in allowed_files:
                        extras.append(relative)
                elif entry.is_dir(follow_symlinks=False):
                    if path not in allowed_directories:
                        extras.append(relative)
                    else:
                        stack.append(path)
                else:
                    unsafe.append(relative)
            except OSError as exc:
                raise ConsumerError(f"cannot inspect kit path {relative}: {exc}") from exc
    if unsafe:
        raise ConsumerError(f"unsafe kit paths: {sorted(unsafe)}")
    extras.sort()
    if extras:
        raise ConsumerError(f"undeclared kit files: {extras}")
    return {
        "files": len(entries),
        "format": LOCK_FORMAT,
        "kit_version": lock_object.get("kit_version"),
        "ok": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = verify(args.root)
    except (ConsumerError, OSError) as exc:
        print(f"softschema conformance consumer: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"conformance integrity passed: {result['files']} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
