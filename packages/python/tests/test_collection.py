"""Collection refresh uses stored inputs, constrained by scope and schema identity."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import softschema.collection as collection
from softschema import CollectionScan, scan_collection

_SCHEMA = """{
  "type": "object", "x-softschema": {"contract": "example:Item/v1"},
  "properties": {"name": {"type": "%s"}}, "required": ["name"]
}"""
_RECORD = "softschema: example:Item/v1\nname: one\n"


def test_refresh_rebinds_without_rereading_the_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema = tmp_path / "item.schema.json"
    record = tmp_path / "item.yaml"
    schema.write_text(_SCHEMA % "string", encoding="utf-8")
    record.write_text(_RECORD, encoding="utf-8")
    initial = scan_collection(tmp_path)
    assert initial.records[0].state == "valid"
    restored = CollectionScan.from_snapshot_json(initial.snapshot_json())

    paths: list[str] = []
    read = collection._read  # pyright: ignore[reportPrivateUsage]

    def observed(path: Path, status: os.stat_result, limit: int) -> str:
        paths.append(path.name)
        return read(path, status, limit)

    with monkeypatch.context() as patch:
        patch.setattr(collection, "_read", observed)
        unchanged = scan_collection(tmp_path, previous=restored)
        assert unchanged.records[0] is restored.records[0]
        assert paths == []

        schema.write_text(_SCHEMA % "integer", encoding="utf-8")
        (tmp_path / "new.yaml").write_text(_RECORD, encoding="utf-8")
        refreshed = scan_collection(tmp_path, previous=unchanged)
        assert paths == ["item.schema.json", "new.yaml"]
        assert refreshed.changed == ("item.schema.json",)
        assert refreshed.added == ("new.yaml",)
        assert [record.state for record in refreshed.records] == ["invalid", "invalid"]

    assert refreshed.records == scan_collection(tmp_path).records
    record.unlink()
    assert scan_collection(tmp_path, previous=refreshed).removed == ("item.yaml",)


def test_scope_limits_and_ambiguous_schema_fallback(tmp_path: Path) -> None:
    (tmp_path / "a.schema.json").write_text(_SCHEMA % "string", encoding="utf-8")
    (tmp_path / "b.schema.json").write_text(_SCHEMA % "integer", encoding="utf-8")
    (tmp_path / "item.yaml").write_text(_RECORD, encoding="utf-8")
    initial = scan_collection(tmp_path)
    assert initial.records[0].errors == ({"kind": "schema_ambiguous"},)
    narrowed = scan_collection(
        tmp_path,
        ignore=lambda path, _is_directory: path == "b.schema.json",
        ignore_id="exclude-b",
        previous=initial,
    )
    assert narrowed.records[0].state == "valid"
    partial = scan_collection(tmp_path, max_entries=2, previous=initial)
    assert not partial.complete
    assert partial.removed == ()
