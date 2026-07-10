"""File-backed YAML boundaries enforce byte limits before whole-file allocation."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from softschema import validate_structural
from softschema.validate import read_frontmatter_with_locations, read_yaml_artifact_with_locations
from softschema.value_domain import DEFAULT_VALIDATION_LIMITS, PortableValueError


def test_file_backed_readers_do_not_use_unbounded_read_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "oversized.yaml"
    source.write_bytes(b"value")
    limits = replace(DEFAULT_VALIDATION_LIMITS, max_resource_bytes=4)

    def forbid_read_bytes(_path: Path) -> bytes:
        raise AssertionError("unbounded Path.read_bytes() reached an untrusted input")

    monkeypatch.setattr(Path, "read_bytes", forbid_read_bytes)
    for reader in (read_frontmatter_with_locations, read_yaml_artifact_with_locations):
        with pytest.raises(PortableValueError, match="maximum resource size exceeded"):
            reader(source, limits)

    structural = validate_structural({}, source, limits=limits)
    assert structural.ok is False
    assert structural.errors[0]["reason"] == "value_domain"
