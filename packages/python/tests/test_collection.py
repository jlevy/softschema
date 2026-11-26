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


def test_partial_schema_discovery_does_not_bind_an_unknown_fallback(tmp_path: Path) -> None:
    schema = _SCHEMA % "string"
    explicit = "softschema:\n  contract: example:Item/v1\n  schema: a.schema.json\nname: one\n"
    (tmp_path / "a.schema.json").write_text(schema)
    (tmp_path / "b.yaml").write_text(_RECORD)
    (tmp_path / "direct.yaml").write_text(explicit)
    (tmp_path / "z.schema.json").write_text(_SCHEMA % "integer")
    partial = scan_collection(tmp_path, max_total_bytes=len(schema + _RECORD + explicit))
    assert not partial.complete
    assert partial.records[0].errors == ({"kind": "schema_discovery_incomplete"},)
    assert partial.records[1].state == "valid"
    assert scan_collection(tmp_path).records[0].errors == ({"kind": "schema_ambiguous"},)


def test_a_byte_limited_refresh_reports_known_deletions(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text(_RECORD)
    removed = tmp_path / "b.yaml"
    removed.write_text(_RECORD)
    oversized = tmp_path / "z.yaml"
    oversized.write_text("name: " + "x" * 100)
    limit = 2 * len(_RECORD)
    initial = scan_collection(tmp_path, max_total_bytes=limit)
    assert not initial.complete
    assert [record.path for record in initial.records] == ["a.yaml", "b.yaml"]
    removed.unlink()
    partial = scan_collection(tmp_path, max_total_bytes=limit, previous=initial)
    assert not partial.complete
    assert partial.removed == ("b.yaml",)
    oversized.unlink()
    complete = scan_collection(tmp_path, max_total_bytes=limit, previous=partial)
    assert complete.complete
    assert complete.removed == ()


def test_incomplete_walk_keeps_known_paths_for_the_next_complete_scan(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text(_RECORD)
    removed = tmp_path / "b.yaml"
    removed.write_text(_RECORD)
    initial = scan_collection(tmp_path, max_entries=2)
    (tmp_path / "c.yaml").write_text(_RECORD)
    partial = scan_collection(tmp_path, max_entries=2, previous=initial)
    assert not partial.complete
    assert partial.removed == ()
    restored = CollectionScan.from_snapshot_json(partial.snapshot_json())
    removed.unlink()
    final = scan_collection(tmp_path, max_entries=2, previous=restored)
    assert final.complete
    assert final.removed == ("b.yaml",)
    assert final.added == ("c.yaml",)


def test_collection_retains_markdown_body_line_endings(tmp_path: Path) -> None:
    body = b"First line\r\nSecond line\r\n"
    metadata = (
        b"---\r\nsoftschema:\r\n  contract: example:Item/v1\r\n  envelope: item\r\n"
        b"title: Document title\r\n"
        b"item:\r\n  name: one\r\n---\r\n"
    )
    (tmp_path / "item.md").write_bytes(metadata + body)
    artifact = scan_collection(tmp_path).records[0]
    assert artifact.body == body.decode()
    assert artifact.host == {"title": "Document title"}
    assert artifact.envelope == "item"
