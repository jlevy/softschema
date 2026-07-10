"""Tests for recursive candidate-transfer checksum verification."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

import devtools.frozen_artifact_smoke as frozen_artifact_smoke
from devtools.frozen_artifact_smoke import (
    MAX_CHECKSUM_BYTES,
    CandidateError,
    main,
    stage_smoke_support,
    verify_transfer_checksums,
    write_transfer_checksums,
)


def test_transfer_checksum_inventory_is_recursive_and_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "artifact.whl").write_bytes(b"wheel")
    nested = tmp_path / "npm-consumer"
    nested.mkdir()
    (nested / "package-lock.json").write_text("{}\n", encoding="utf-8")

    def forbid_read_bytes(_path: Path) -> bytes:
        raise AssertionError("candidate hashing must stream regular files")

    monkeypatch.setattr(Path, "read_bytes", forbid_read_bytes)
    write_transfer_checksums(tmp_path)
    verify_transfer_checksums(tmp_path)

    (nested / "package-lock.json").write_text("changed\n", encoding="utf-8")
    with pytest.raises(CandidateError, match="digest mismatch"):
        verify_transfer_checksums(tmp_path)


def test_transfer_inventory_does_not_use_cached_directory_entry_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Python 3.11 DirEntry identity fields are zero on Windows."""
    (tmp_path / "artifact.whl").write_bytes(b"wheel")
    original_scandir = os.scandir

    class EntryWithoutTrustedStat:
        def __init__(self, entry: os.DirEntry[str]) -> None:
            self.name = entry.name
            self.path = entry.path

        def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
            del follow_symlinks
            raise AssertionError("candidate inventory must use a fresh path stat")

    class ScandirWithoutTrustedStat:
        def __init__(self, path: str | os.PathLike[str]) -> None:
            self._entries = original_scandir(path)

        def __enter__(self) -> ScandirWithoutTrustedStat:
            return self

        def __exit__(self, *_args: object) -> None:
            self._entries.close()

        def __iter__(self) -> Iterator[EntryWithoutTrustedStat]:
            return (EntryWithoutTrustedStat(entry) for entry in self._entries)

    monkeypatch.setattr(os, "scandir", ScandirWithoutTrustedStat)
    write_transfer_checksums(tmp_path)
    verify_transfer_checksums(tmp_path)


def test_transfer_inventory_compares_descriptor_metadata_across_stat_interfaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows path-stat timestamps can differ from descriptor timestamps."""
    subject = tmp_path / "artifact.whl"
    subject.write_bytes(b"wheel")
    original_lstat = Path.lstat

    def lstat_with_path_timestamp_skew(path: Path) -> os.stat_result:
        result = original_lstat(path)
        if path == subject:
            fields = list(result)
            fields[8] += 1
            return os.stat_result(fields)
        return result

    monkeypatch.setattr(Path, "lstat", lstat_with_path_timestamp_skew)
    write_transfer_checksums(tmp_path)
    verify_transfer_checksums(tmp_path)


def test_transfer_checksum_rejects_extra_or_traversing_files(tmp_path: Path) -> None:
    (tmp_path / "artifact.whl").write_bytes(b"wheel")
    write_transfer_checksums(tmp_path)
    (tmp_path / "extra.tgz").write_bytes(b"extra")
    with pytest.raises(CandidateError, match="inventory mismatch"):
        verify_transfer_checksums(tmp_path)

    (tmp_path / "extra.tgz").unlink()
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "SHA256SUMS").write_text("not the root inventory\n", encoding="utf-8")
    with pytest.raises(CandidateError, match="inventory mismatch"):
        verify_transfer_checksums(tmp_path)

    (nested / "SHA256SUMS").unlink()
    with pytest.raises(CandidateError, match="unexpected directories"):
        verify_transfer_checksums(tmp_path)

    nested.rmdir()
    checksums = tmp_path / "SHA256SUMS"
    checksums.write_bytes(b"x" * (MAX_CHECKSUM_BYTES + 1))
    with pytest.raises(CandidateError, match="inventory is oversized"):
        verify_transfer_checksums(tmp_path)

    checksums.write_text("", encoding="utf-8")
    with pytest.raises(CandidateError, match="inventory is empty"):
        verify_transfer_checksums(tmp_path)

    checksums.write_text("0" * 64 + "  ../escape\n", encoding="utf-8")
    with pytest.raises(CandidateError, match="unsafe checksum path"):
        verify_transfer_checksums(tmp_path)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="platform has no FIFO support")
def test_transfer_checksum_rejects_non_regular_nodes(tmp_path: Path) -> None:
    (tmp_path / "artifact.whl").write_bytes(b"wheel")
    fifo = tmp_path / "unexpected.fifo"
    os.mkfifo(fifo)
    with pytest.raises(CandidateError, match="non-regular node"):
        write_transfer_checksums(tmp_path)

    fifo.unlink()
    write_transfer_checksums(tmp_path)
    os.mkfifo(fifo)
    with pytest.raises(CandidateError, match="non-regular node"):
        verify_transfer_checksums(tmp_path)


@pytest.mark.parametrize("hidden_kind", ["file", "directory"])
def test_transfer_checksum_rejects_hidden_nodes(tmp_path: Path, hidden_kind: str) -> None:
    (tmp_path / "artifact.whl").write_bytes(b"wheel")
    hidden = tmp_path / ".hidden"
    if hidden_kind == "file":
        hidden.write_bytes(b"hidden")
    else:
        hidden.mkdir()
        (hidden / "subject").write_bytes(b"hidden")

    with pytest.raises(CandidateError, match="hidden node"):
        write_transfer_checksums(tmp_path)


def test_transfer_checksum_bounds_actual_inventory_and_generated_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ["one.whl", "two.whl", "three.whl"]:
        (tmp_path / name).write_bytes(name.encode())

    with pytest.raises(CandidateError, match="2-node limit"):
        frozen_artifact_smoke._candidate_files(tmp_path, max_nodes=2)

    monkeypatch.setattr(frozen_artifact_smoke, "MAX_CHECKSUM_BYTES", 70)
    with pytest.raises(CandidateError, match="generated checksum inventory is oversized"):
        write_transfer_checksums(tmp_path)
    assert not (tmp_path / "SHA256SUMS").exists()


def test_transfer_checksum_bounds_file_and_aggregate_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "one.whl").write_bytes(b"12345")
    monkeypatch.setattr(frozen_artifact_smoke, "MAX_CANDIDATE_FILE_BYTES", 4)
    with pytest.raises(CandidateError, match="file exceeds the byte limit"):
        write_transfer_checksums(tmp_path)

    monkeypatch.setattr(frozen_artifact_smoke, "MAX_CANDIDATE_FILE_BYTES", 10)
    monkeypatch.setattr(frozen_artifact_smoke, "MAX_CANDIDATE_TOTAL_BYTES", 8)
    (tmp_path / "two.whl").write_bytes(b"12345")
    with pytest.raises(CandidateError, match="aggregate exceeds the byte limit"):
        write_transfer_checksums(tmp_path)


def test_transfer_checksum_rejects_a_file_that_grows_while_hashing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = tmp_path / "artifact.whl"
    subject.write_bytes(b"four")
    original_read = os.read
    appended = False

    def read_then_grow(descriptor: int, size: int) -> bytes:
        nonlocal appended
        chunk = original_read(descriptor, size)
        if chunk and not appended:
            with subject.open("ab") as stream:
                stream.write(b"+")
            appended = True
        return chunk

    monkeypatch.setattr(os, "read", read_then_grow)
    with pytest.raises(CandidateError, match="changed while hashing"):
        frozen_artifact_smoke._sha256(tmp_path, subject.name)


def test_transfer_checksum_rejects_a_reparse_redirect_at_the_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_stat = tmp_path.lstat()
    reparse_stat = cast(
        os.stat_result,
        cast(
            object,
            SimpleNamespace(
                st_mode=root_stat.st_mode,
                st_dev=root_stat.st_dev,
                st_ino=root_stat.st_ino,
                st_reparse_tag=1,
            ),
        ),
    )
    assert frozen_artifact_smoke._is_redirect(reparse_stat)

    original_lstat = Path.lstat

    def lstat_with_reparse_root(path: Path) -> os.stat_result:
        if path == tmp_path:
            return reparse_stat
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", lstat_with_reparse_root)
    with pytest.raises(CandidateError, match="candidate must be a directory"):
        frozen_artifact_smoke._candidate_files(tmp_path)


def test_checksum_cli_rejects_a_redirected_candidate_root(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "artifact.whl").write_bytes(b"wheel")
    write_transfer_checksums(candidate)
    alias = tmp_path / "candidate-alias"
    try:
        alias.symlink_to(candidate, target_is_directory=True)
    except OSError:
        pytest.skip("platform does not permit test symlinks")

    with pytest.raises(CandidateError, match="regular SHA256SUMS"):
        main(["verify-checksums", str(alias)])


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction regression")
def test_checksum_cli_rejects_a_windows_junction_root(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "artifact.whl").write_bytes(b"wheel")
    write_transfer_checksums(candidate)
    junction = tmp_path / "candidate-junction"
    created = subprocess.run(
        ["cmd", "/d", "/c", "mklink", "/J", str(junction), str(candidate)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert created.returncode == 0, created.stderr

    with pytest.raises(CandidateError, match="regular SHA256SUMS"):
        main(["verify-checksums", str(junction)])


def test_transfer_checksum_rejects_a_nested_reparse_redirect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nested = tmp_path / "junction"
    nested.mkdir()
    nested_stat = nested.lstat()
    nested_identity = (nested_stat.st_dev, nested_stat.st_ino)
    original_is_redirect = frozen_artifact_smoke._is_redirect

    def mark_nested_as_redirect(source_stat: os.stat_result) -> bool:
        return (source_stat.st_dev, source_stat.st_ino) == nested_identity or (
            original_is_redirect(source_stat)
        )

    monkeypatch.setattr(
        frozen_artifact_smoke,
        "_is_redirect",
        mark_nested_as_redirect,
    )
    with pytest.raises(CandidateError, match="candidate contains a redirect"):
        frozen_artifact_smoke._candidate_files(tmp_path)


def test_transfer_checksum_rejects_a_subject_swapped_to_a_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    subject = candidate / "artifact.whl"
    subject.write_bytes(b"expected")
    write_transfer_checksums(candidate)
    outside = tmp_path / "outside.whl"
    outside.write_bytes(b"outside")
    outside_digest = hashlib.sha256(b"outside").hexdigest()
    (candidate / "SHA256SUMS").write_text(
        f"{outside_digest}  artifact.whl\n",
        encoding="utf-8",
    )
    original_candidate_files = frozen_artifact_smoke._candidate_files

    def swap_after_inventory(
        directory: Path,
        *,
        expected_names: set[str] | None = None,
        max_nodes: int | None = None,
    ) -> dict[str, frozen_artifact_smoke._FileSnapshot]:
        files = original_candidate_files(
            directory,
            expected_names=expected_names,
            max_nodes=max_nodes,
        )
        subject.unlink()
        subject.symlink_to(outside)
        return files

    monkeypatch.setattr(frozen_artifact_smoke, "_candidate_files", swap_after_inventory)
    with pytest.raises(CandidateError, match="checksum subject is not regular"):
        verify_transfer_checksums(candidate)


def test_transfer_checksum_rejects_a_parent_swapped_to_a_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = tmp_path / "candidate"
    nested = candidate / "nested"
    nested.mkdir(parents=True)
    subject = nested / "artifact.whl"
    subject.write_bytes(b"expected")
    write_transfer_checksums(candidate)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "artifact.whl").write_bytes(b"outside")
    outside_digest = hashlib.sha256(b"outside").hexdigest()
    (candidate / "SHA256SUMS").write_text(
        f"{outside_digest}  nested/artifact.whl\n",
        encoding="utf-8",
    )
    original_candidate_files = frozen_artifact_smoke._candidate_files

    def swap_parent_after_inventory(
        directory: Path,
        *,
        expected_names: set[str] | None = None,
        max_nodes: int | None = None,
    ) -> dict[str, frozen_artifact_smoke._FileSnapshot]:
        files = original_candidate_files(
            directory,
            expected_names=expected_names,
            max_nodes=max_nodes,
        )
        subject.unlink()
        nested.rmdir()
        try:
            nested.symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("platform does not permit test symlinks")
        return files

    monkeypatch.setattr(
        frozen_artifact_smoke,
        "_candidate_files",
        swap_parent_after_inventory,
    )
    with pytest.raises(CandidateError, match="checksum subject is not regular"):
        verify_transfer_checksums(candidate)


def test_transfer_checksum_rejects_a_subject_replaced_after_hashing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    subject = candidate / "artifact.whl"
    subject.write_bytes(b"expected")
    write_transfer_checksums(candidate)
    original_sha256 = frozen_artifact_smoke._sha256
    swapped = False

    def hash_then_swap(
        directory: Path,
        name: str,
    ) -> tuple[str, frozen_artifact_smoke._FileSnapshot]:
        nonlocal swapped
        result = original_sha256(directory, name)
        if name == "artifact.whl" and not swapped:
            replacement = candidate / "replacement.whl"
            replacement.write_bytes(b"evil")
            replacement.replace(subject)
            swapped = True
        return result

    monkeypatch.setattr(frozen_artifact_smoke, "_sha256", hash_then_swap)
    with pytest.raises(CandidateError, match="inventory changed during verification"):
        verify_transfer_checksums(candidate)


def test_transfer_checksum_rejects_inventory_replaced_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "artifact.whl").write_bytes(b"expected")
    write_transfer_checksums(candidate)
    inventory = candidate / "SHA256SUMS"
    original_read_checksum = frozen_artifact_smoke._read_checksum_text
    replaced = False

    def read_then_replace(
        directory: Path,
    ) -> tuple[str, frozen_artifact_smoke._FileSnapshot]:
        nonlocal replaced
        result = original_read_checksum(directory)
        replacement = candidate / "replacement"
        replacement.write_bytes(inventory.read_bytes())
        replacement.replace(inventory)
        replaced = True
        return result

    monkeypatch.setattr(frozen_artifact_smoke, "_read_checksum_text", read_then_replace)
    with pytest.raises(CandidateError, match="inventory changed during verification"):
        verify_transfer_checksums(candidate)
    assert replaced


def test_fallback_open_rejects_a_transient_parent_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = tmp_path / "candidate"
    nested = candidate / "nested"
    parked = candidate / "nested-original"
    outside = tmp_path / "outside"
    nested.mkdir(parents=True)
    outside.mkdir()
    subject = nested / "artifact.whl"
    subject.write_bytes(b"expected")
    (outside / subject.name).write_bytes(b"outside")
    try:
        probe = tmp_path / "probe"
        probe.symlink_to(outside, target_is_directory=True)
        probe.unlink()
    except OSError:
        pytest.skip("platform does not permit test directory symlinks")

    monkeypatch.setattr(os, "supports_dir_fd", set())
    original_lstat = Path.lstat
    original_open = os.open
    substituted = False

    def lstat_then_substitute(path: Path) -> os.stat_result:
        nonlocal substituted
        result = original_lstat(path)
        if path == nested and not substituted:
            nested.rename(parked)
            nested.symlink_to(outside, target_is_directory=True)
            substituted = True
        return result

    def open_then_restore(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        if substituted and Path(os.fsdecode(path)) == subject:
            nested.unlink()
            parked.rename(nested)
        return descriptor

    monkeypatch.setattr(Path, "lstat", lstat_then_substitute)
    monkeypatch.setattr(os, "open", open_then_restore)
    with pytest.raises(CandidateError, match="file identity changed"):
        frozen_artifact_smoke._sha256(candidate, "nested/artifact.whl")


def test_transferred_checksum_verifier_does_not_mutate_candidate(tmp_path: Path) -> None:
    stage_smoke_support(tmp_path)
    write_transfer_checksums(tmp_path)
    environment = os.environ.copy()
    environment.pop("PYTHONDONTWRITEBYTECODE", None)
    environment.pop("PYTHONPYCACHEPREFIX", None)

    process = subprocess.run(
        [
            sys.executable,
            str(tmp_path / "devtools" / "frozen_artifact_smoke.py"),
            "verify-checksums",
            str(tmp_path),
        ],
        cwd=tmp_path.parent,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        check=False,
    )

    assert process.returncode == 0, process.stderr
    assert not list(tmp_path.rglob("*.pyc"))
    assert not list(tmp_path.rglob("__pycache__"))


def test_transferred_verifier_does_not_import_unauthenticated_helpers(tmp_path: Path) -> None:
    stage_smoke_support(tmp_path)
    write_transfer_checksums(tmp_path)
    sentinel = tmp_path / "helper-executed"
    helper = tmp_path / "devtools" / "installed_artifact_smoke.py"
    original = helper.read_text(encoding="utf-8")
    future_import = "from __future__ import annotations\n"
    assert future_import in original
    helper.write_text(
        original.replace(
            future_import,
            (
                f"{future_import}from pathlib import Path\n"
                f"Path({str(sentinel)!r}).write_text('executed', encoding='utf-8')\n"
            ),
            1,
        ),
        encoding="utf-8",
    )

    process = subprocess.run(
        [
            sys.executable,
            str(tmp_path / "devtools" / "frozen_artifact_smoke.py"),
            "verify-checksums",
            str(tmp_path),
        ],
        cwd=tmp_path.parent,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert process.returncode != 0
    assert "digest mismatch" in process.stderr
    assert not sentinel.exists()
