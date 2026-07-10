"""File-backed YAML boundaries enforce byte limits before whole-file allocation."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import BaseModel
from typing_extensions import override

from softschema import Contract, SchemaView, compile_model, validate_artifact, validate_structural
from softschema._bounded_file import read_bounded_bytes
from softschema.compile import _render_schema_within_limit, _yaml_dump
from softschema.validate import (
    capture_validated_schema_source,
    read_frontmatter_with_locations,
    read_yaml_artifact_with_locations,
    take_validated_schema_source,
)
from softschema.value_domain import (
    DEFAULT_VALIDATION_LIMITS,
    PortableValueError,
    normalize_portable_value,
)

_METADATA_PATH_VECTORS = json.loads(
    (Path(__file__).parents[3] / "tests/parity/metadata-schema-paths.json").read_text(
        encoding="utf-8"
    )
)["document_schema_path"]


class _CompiledSchemaModel(BaseModel):
    value: str


class _ConstOneSchemaModel(BaseModel):
    @classmethod
    @override
    def model_json_schema(cls, *args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        return {"const": 1}


class _FinalNodeBudgetSchemaModel(BaseModel):
    @classmethod
    @override
    def model_json_schema(cls, *args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        # This value fits immediately before compiler metadata gets its digest field.
        return {"type": "object", "enum": [None] * 99_987}


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
    with pytest.raises(PortableValueError, match="maximum resource size exceeded"):
        SchemaView.load(source, limits=limits)

    structural = validate_structural({}, source, limits=limits)
    assert structural.ok is False
    assert structural.errors[0]["reason"] == "value_domain"


def test_schema_view_rejects_an_oversized_snapshot_before_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "oversized.schema.yaml"
    source.write_bytes(b"value")
    reads: list[int] = []
    original_read = os.read

    def tracked_read(descriptor: int, size: int) -> bytes:
        reads.append(size)
        return original_read(descriptor, size)

    monkeypatch.setattr(os, "read", tracked_read)
    limits = replace(DEFAULT_VALIDATION_LIMITS, max_resource_bytes=4)

    with pytest.raises(PortableValueError, match="maximum resource size exceeded"):
        SchemaView.load(source, limits=limits)

    assert reads == []


def test_bounded_reader_loops_across_short_regular_file_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "schema.yaml"
    expected = b"type: object\n"
    source.write_bytes(expected)
    original_read = os.read
    calls = 0

    def short_read(descriptor: int, size: int) -> bytes:
        nonlocal calls
        calls += 1
        return original_read(descriptor, min(size, 1))

    monkeypatch.setattr(os, "read", short_read)
    assert read_bounded_bytes(source, len(expected)) == expected
    assert calls == len(expected) + 1


def test_bounded_reader_rejects_premature_eof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "schema.yaml"
    source.write_bytes(b"abcdef")
    original_read = os.read
    calls = 0

    def truncated_read(descriptor: int, size: int) -> bytes:
        nonlocal calls
        calls += 1
        return original_read(descriptor, 1) if calls == 1 else b""

    monkeypatch.setattr(os, "read", truncated_read)
    with pytest.raises(OSError, match="changed before it could be opened"):
        read_bounded_bytes(source, 6)


def test_bounded_reader_rejects_same_size_mutation_even_when_mtime_is_restored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "schema.yaml"
    source.write_bytes(b"AAAA")
    original = source.stat()
    original_read = os.read
    calls = 0

    def mutate_after_first_byte(descriptor: int, size: int) -> bytes:
        nonlocal calls
        chunk = original_read(descriptor, min(size, 1))
        calls += 1
        if calls == 1:
            mutation = os.open(source, os.O_WRONLY)
            try:
                os.write(mutation, b"BBBB")
            finally:
                os.close(mutation)
            os.utime(source, ns=(original.st_atime_ns, original.st_mtime_ns))
        return chunk

    monkeypatch.setattr(os, "read", mutate_after_first_byte)
    with pytest.raises(OSError, match="changed before it could be opened"):
        read_bounded_bytes(source, 4)


def test_bounded_reader_fails_closed_without_a_stable_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "schema.yaml"
    source.write_bytes(b"{}")
    original_lstat = Path.lstat

    def zero_inode(value: Path) -> os.stat_result:
        result = original_lstat(value)
        fields = list(result)
        fields[1] = 0
        return os.stat_result(fields)

    monkeypatch.setattr(Path, "lstat", zero_inode)
    with pytest.raises(OSError, match="changed before it could be opened"):
        read_bounded_bytes(source, 2)


def test_bounded_reader_normalizes_a_symlink_loop_to_oserror(tmp_path: Path) -> None:
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    try:
        first.symlink_to(second.name)
        second.symlink_to(first.name)
    except OSError:
        pytest.skip("platform does not permit test symlinks")
    with pytest.raises(OSError, match=r"(?i)too many (?:levels of )?symbolic links"):
        read_bounded_bytes(first, 16)


def test_compile_check_rejects_an_oversized_snapshot_before_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "oversized.schema.yaml"
    max_bytes = DEFAULT_VALIDATION_LIMITS.max_resource_bytes
    with output.open("wb") as stream:
        stream.truncate(max_bytes + 1)
    reads: list[int] = []
    original_read = os.read

    def tracked_read(descriptor: int, size: int) -> bytes:
        reads.append(size)
        return original_read(descriptor, size)

    monkeypatch.setattr(os, "read", tracked_read)

    with pytest.raises(PortableValueError, match="maximum resource size exceeded"):
        compile_model(
            _CompiledSchemaModel,
            output,
            contract_id="example:BoundedSchema/v1",
            check_only=True,
        )

    assert reads == []


def test_compile_check_decodes_committed_schema_as_strict_utf8(tmp_path: Path) -> None:
    output = tmp_path / "invalid.schema.yaml"
    output.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        compile_model(
            _CompiledSchemaModel,
            output,
            contract_id="example:BoundedSchema/v1",
            check_only=True,
        )


@pytest.mark.parametrize(
    "committed",
    [
        ".nan\n",
        "&shared [*shared]\n",
        "[" * 130 + "0" + "]" * 130 + "\n",
    ],
)
def test_compile_check_applies_the_portable_yaml_boundary(
    tmp_path: Path,
    committed: str,
) -> None:
    output = tmp_path / "nonportable.schema.yaml"
    output.write_text(committed, encoding="utf-8")
    with pytest.raises(PortableValueError):
        compile_model(
            _CompiledSchemaModel,
            output,
            contract_id="example:BoundedSchema/v1",
            check_only=True,
        )


def test_compile_check_treats_a_directory_as_missing(tmp_path: Path) -> None:
    output = tmp_path / "schema.yaml"
    output.mkdir()
    result = compile_model(
        _CompiledSchemaModel,
        output,
        contract_id="example:BoundedSchema/v1",
        check_only=True,
    )
    assert result.drift is True
    assert result.drift_diff == f"missing committed compiled schema at {output}"


def test_compile_check_distinguishes_json_boolean_from_integer(tmp_path: Path) -> None:
    output = tmp_path / "const.schema.yaml"
    compile_model(
        _ConstOneSchemaModel,
        output,
        contract_id="example:ConstOne/v1",
    )
    committed = output.read_text(encoding="utf-8")
    assert "const: 1" in committed
    output.write_text(committed.replace("const: 1", "const: true", 1), encoding="utf-8")

    result = compile_model(
        _ConstOneSchemaModel,
        output,
        contract_id="example:ConstOne/v1",
        check_only=True,
    )
    assert result.drift is True


def test_compiler_charges_digest_metadata_against_final_node_budget(tmp_path: Path) -> None:
    with pytest.raises(PortableValueError, match="maximum node count exceeded"):
        compile_model(
            _FinalNodeBudgetSchemaModel,
            tmp_path / "too-many-final-nodes.schema.yaml",
            contract_id="example:FinalNodeBudget/v1",
        )


def test_compiler_falls_back_to_canonical_json_when_yaml_exceeds_reader_limit(
    tmp_path: Path,
) -> None:
    limit = DEFAULT_VALIDATION_LIMITS.max_resource_bytes
    description = "x\n" * (DEFAULT_VALIDATION_LIMITS.max_scalar_codepoints // 2)
    schema = {
        "type": "object",
        "properties": {
            "p0": {"type": "string", "description": description},
            "p1": {"type": "string", "description": description},
        },
    }
    normalized, canonical_size = normalize_portable_value(schema)
    assert canonical_size < limit
    assert isinstance(normalized, dict)
    rendered = _yaml_dump(normalized)
    assert len(rendered.encode("utf-8")) > limit
    portable = _render_schema_within_limit(normalized)
    assert portable.startswith("{")
    assert len(portable.encode("utf-8")) < limit
    output = tmp_path / "fallback.schema.yaml"
    output.write_text(portable, encoding="utf-8")
    assert SchemaView.load(output).raw == normalized


def test_compiler_accepts_the_shared_near_limit_no_wrap_shape(tmp_path: Path) -> None:
    description = "x " * (1_047_500 // 2)
    schema = {
        "type": "object",
        "properties": {
            f"p{index}": {"type": "string", "description": description} for index in range(8)
        },
    }
    normalized, _size = normalize_portable_value(schema)
    assert isinstance(normalized, dict)
    rendered = _render_schema_within_limit(normalized)
    assert len(rendered.encode("utf-8")) == 8_380_369
    output = tmp_path / "near-limit.schema.yaml"
    output.write_text(rendered, encoding="utf-8")
    assert SchemaView.load(output).raw == normalized


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="platform has no FIFO support")
def test_bounded_reader_rejects_fifo_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fifo = tmp_path / "schema.fifo"
    os.mkfifo(fifo)

    def forbid_open(*_args: object, **_kwargs: object) -> int:
        raise AssertionError("non-regular nodes must be rejected before open")

    monkeypatch.setattr(os, "open", forbid_open)
    with pytest.raises(OSError, match="bounded input must be a regular file"):
        read_bounded_bytes(fifo, 4)


def test_bounded_reader_resolves_symlinks_to_one_stable_regular_file(tmp_path: Path) -> None:
    target = tmp_path / "schema.yaml"
    target.write_text("type: object\n", encoding="utf-8")
    linked_directory = tmp_path / "linked"
    try:
        linked_directory.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("platform does not permit test symlinks")
    assert read_bounded_bytes(linked_directory / target.name, 1024) == target.read_bytes()


def test_bounded_reader_rejects_identity_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "schema.yaml"
    source.write_text("type: object\n", encoding="utf-8")
    original_fstat = os.fstat

    def mismatched_fstat(descriptor: int) -> os.stat_result:
        result = original_fstat(descriptor)
        fields = list(result)
        fields[1] = result.st_ino + 1
        return os.stat_result(fields)

    monkeypatch.setattr(os, "fstat", mismatched_fstat)
    with pytest.raises(OSError, match="changed before it could be opened"):
        read_bounded_bytes(source, 1024)


def test_bounded_reader_rejects_parent_substitution_during_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorized = tmp_path / "authorized"
    outside = tmp_path / "outside"
    parked = tmp_path / "authorized-original"
    authorized.mkdir()
    outside.mkdir()
    source = authorized / "schema.yaml"
    source.write_text("type: object\n", encoding="utf-8")
    (outside / source.name).write_text("outside\n", encoding="utf-8")
    original_resolve = Path.resolve
    swapped = False

    def resolve_then_swap(
        value: Path,
        strict: bool = False,
    ) -> Path:
        nonlocal swapped
        resolved = original_resolve(value, strict=strict)
        if value == source and not swapped:
            authorized.rename(parked)
            try:
                authorized.symlink_to(outside, target_is_directory=True)
            except OSError:
                parked.rename(authorized)
                pytest.skip("platform does not permit test directory symlinks")
            swapped = True
        return resolved

    monkeypatch.setattr(Path, "resolve", resolve_then_swap)
    try:
        with pytest.raises(OSError, match="changed before it could be opened"):
            read_bounded_bytes(source, 1024)
    finally:
        if swapped:
            authorized.unlink()
            parked.rename(authorized)


def test_metadata_schema_authorization_survives_parent_substitution(
    tmp_path: Path,
) -> None:
    documents = tmp_path / "documents"
    outside = tmp_path / "outside"
    parked = tmp_path / "documents-original"
    documents.mkdir()
    outside.mkdir()
    schema = documents / "record.schema.yaml"
    schema.write_text("type: object\n", encoding="utf-8")
    (outside / schema.name).write_text("type: object\n", encoding="utf-8")
    artifact = documents / "record.md"
    artifact_text = (
        "---\n"
        "softschema:\n"
        "  contract: example:BoundedRecord/v1\n"
        "  schema: record.schema.yaml\n"
        "  envelope: record\n"
        "record:\n"
        "  value: accepted\n"
        "---\n"
        "body\n"
    )
    artifact.write_text(artifact_text, encoding="utf-8")
    (outside / artifact.name).write_text(artifact_text, encoding="utf-8")
    located = read_frontmatter_with_locations(artifact)
    documents.rename(parked)
    try:
        documents.symlink_to(outside, target_is_directory=True)
    except OSError:
        parked.rename(documents)
        pytest.skip("platform does not permit test directory symlinks")
    try:
        result = validate_artifact(
            artifact,
            contract=Contract(id="example:BoundedRecord/v1", envelope_key="record"),
            frontmatter=located.value,
            source_file=located.source_file,
        )
    finally:
        documents.unlink()
        parked.rename(documents)

    assert result.structural.ok is False
    assert result.structural.errors[0]["kind"] == "schema_missing"


def test_missing_metadata_schema_through_escaping_symlink_reports_escape(
    tmp_path: Path,
) -> None:
    documents = tmp_path / "documents"
    outside = tmp_path / "outside"
    documents.mkdir()
    outside.mkdir()
    try:
        (documents / "escape").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("platform does not permit test directory symlinks")
    artifact = documents / "record.md"
    artifact.write_text(
        "---\n"
        "softschema:\n"
        "  contract: example:BoundedRecord/v1\n"
        "  schema: escape/missing.schema.yaml\n"
        "  envelope: record\n"
        "record:\n"
        "  value: accepted\n"
        "---\n",
        encoding="utf-8",
    )

    result = validate_artifact(
        artifact,
        contract=Contract(id="example:BoundedRecord/v1", envelope_key="record"),
    )

    assert result.structural.ok is False
    assert result.structural.errors[0]["kind"] == "schema_missing"
    assert "escapes the document directory" in result.structural.errors[0]["message"]


def test_schema_diagnostics_retain_the_exact_validated_source_map(tmp_path: Path) -> None:
    schema = tmp_path / "record.schema.yaml"
    schema.write_text("type: 7\n", encoding="utf-8")
    artifact = tmp_path / "record.md"
    artifact.write_text(
        "---\nrecord:\n  value: accepted\n---\n",
        encoding="utf-8",
    )
    with capture_validated_schema_source():
        result = validate_artifact(
            artifact,
            contract=Contract(
                id="example:BoundedRecord/v1",
                envelope_key="record",
                schema_path=schema,
            ),
        )
    assert result.structural.ok is False

    schema.write_text("type: object\n", encoding="utf-8")
    validated_source = take_validated_schema_source(result.structural)

    assert validated_source is not None
    source_path, source_map = validated_source
    assert source_path == schema.resolve()
    assert source_map.span("/type") is not None
    assert take_validated_schema_source(result.structural) is None


@pytest.mark.parametrize(
    "contents",
    [
        b"x" * (DEFAULT_VALIDATION_LIMITS.max_resource_bytes + 1),
        b"\xff",
        b"type: [\n",
    ],
    ids=["oversized", "invalid-utf8", "invalid-yaml"],
)
def test_failed_schema_diagnostics_retain_empty_exact_source(
    tmp_path: Path,
    contents: bytes,
) -> None:
    schema = tmp_path / "record.schema.yaml"
    schema.write_bytes(contents)
    artifact = tmp_path / "record.md"
    artifact.write_text("---\nrecord: {}\n---\n", encoding="utf-8")
    with capture_validated_schema_source():
        result = validate_artifact(
            artifact,
            contract=Contract(
                id="example:BoundedRecord/v1",
                envelope_key="record",
                schema_path=schema,
            ),
        )
    assert result.structural.ok is False

    schema.write_text("type: 7\n", encoding="utf-8")
    validated_source = take_validated_schema_source(result.structural)

    assert validated_source is not None
    source_path, source_map = validated_source
    assert source_path == schema.resolve()
    assert source_map.span("/type") is None


@pytest.mark.parametrize(
    "code_point",
    _METADATA_PATH_VECTORS["rejected_code_points"],
    ids=lambda code_point: f"U+{code_point:04X}",
)
def test_document_controlled_schema_path_rejects_c0_and_del(
    tmp_path: Path,
    code_point: int,
) -> None:
    artifact = tmp_path / "record.md"
    schema_value = json.dumps(f"prefix{chr(code_point)}suffix", ensure_ascii=True)
    artifact.write_text(
        "---\n"
        "softschema:\n"
        "  contract: example:BoundedRecord/v1\n"
        f"  schema: {schema_value}\n"
        "  envelope: record\n"
        "record: {}\n"
        "---\n",
        encoding="utf-8",
    )

    result = validate_artifact(
        artifact,
        contract=Contract(id="example:BoundedRecord/v1", envelope_key="record"),
    )

    assert result.structural.ok is False
    assert result.structural.errors[0]["kind"] == _METADATA_PATH_VECTORS["expected_kind"]
