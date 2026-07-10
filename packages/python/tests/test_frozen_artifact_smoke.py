"""Tests for recursive candidate-transfer checksum verification."""

from __future__ import annotations

from pathlib import Path

import pytest

from devtools.frozen_artifact_smoke import (
    CandidateError,
    verify_transfer_checksums,
    write_transfer_checksums,
)


def test_transfer_checksum_inventory_is_recursive_and_exact(tmp_path: Path) -> None:
    (tmp_path / "artifact.whl").write_bytes(b"wheel")
    nested = tmp_path / "npm-consumer"
    nested.mkdir()
    (nested / "package-lock.json").write_text("{}\n", encoding="utf-8")

    write_transfer_checksums(tmp_path)
    verify_transfer_checksums(tmp_path)

    (nested / "package-lock.json").write_text("changed\n", encoding="utf-8")
    with pytest.raises(CandidateError, match="digest mismatch"):
        verify_transfer_checksums(tmp_path)


def test_transfer_checksum_rejects_extra_or_traversing_files(tmp_path: Path) -> None:
    (tmp_path / "artifact.whl").write_bytes(b"wheel")
    write_transfer_checksums(tmp_path)
    (tmp_path / "extra.tgz").write_bytes(b"extra")
    with pytest.raises(CandidateError, match="inventory mismatch"):
        verify_transfer_checksums(tmp_path)

    (tmp_path / "extra.tgz").unlink()
    checksums = tmp_path / "SHA256SUMS"
    checksums.write_text("0" * 64 + "  ../escape\n", encoding="utf-8")
    with pytest.raises(CandidateError, match="unsafe checksum path"):
        verify_transfer_checksums(tmp_path)
