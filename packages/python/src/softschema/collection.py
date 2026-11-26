"""Bounded, read-only discovery and structural validation of a directory of artifacts."""

from __future__ import annotations

import os
import stat
from collections import Counter, defaultdict
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path, PureWindowsPath
from typing import Any, Literal, cast

from pydantic import TypeAdapter

from softschema._portable import (
    MAX_SAFE_INTEGER,
    PortableInputError,
    opens_frontmatter_fence,
    split_frontmatter,
)
from softschema.compile import _schema_sha256
from softschema.conform import _conform_text
from softschema.models import (
    Contract,
    SchemaMetadata,
    SchemaProfile,
    SchemaStatus,
    ValidationExecution,
    parse_schema_metadata,
)
from softschema.repair import repair_yaml_text
from softschema.schema_view import SchemaView
from softschema.validate import (
    StructuralResult,
    infer_envelope_key,
    parse_frontmatter_text,
    parse_yaml_text,
    validate_artifact,
    validate_structural_text,
)

RecordState = Literal["valid", "repaired", "invalid", "unbound", "unreadable", "malformed"]
_SCHEMA_SUFFIXES = (".schema.yaml", ".schema.yml", ".schema.json")
_ARTIFACT_SUFFIXES = frozenset({".md", ".yaml", ".yml", ".json"})
_SNAPSHOT_VERSION = 3


@dataclass(frozen=True)
class CollectionSchema:
    path: str
    digest: str
    contract: str | None
    document: dict[str, Any]

    def view(self) -> SchemaView:
        return SchemaView(self.document)


@dataclass(frozen=True)
class CollectionRecord:
    path: str
    profile: SchemaProfile
    state: RecordState
    metadata: SchemaMetadata | None = None
    values: dict[str, Any] | None = None
    host: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    schema: str | None = None
    errors: tuple[dict[str, Any], ...] = ()
    repairs: tuple[dict[str, Any], ...] = ()
    envelope: str | None = None
    execution: ValidationExecution = "not_run"


@dataclass(frozen=True)
class _ScannedFile:
    stamp: tuple[int, ...]
    record: CollectionRecord | None = None
    record_yaml: str = ""
    schema: CollectionSchema | None = None
    schema_text: str | None = None
    problem: str | None = None


@dataclass(frozen=True)
class CollectionScan:
    records: tuple[CollectionRecord, ...]
    schemas: tuple[CollectionSchema, ...]
    problems: tuple[dict[str, str], ...]
    complete: bool
    added: tuple[str, ...]
    changed: tuple[str, ...]
    removed: tuple[str, ...]
    _version: int
    _scope: tuple[str, bool, str | None, int, int, int]
    _files: dict[str, _ScannedFile]
    _known_stamps: dict[str, tuple[int, ...]]
    _bound_records: tuple[CollectionRecord, ...]

    def snapshot_json(self) -> str:
        """Serialize Python refresh data for a trusted local cache."""
        return _SNAPSHOT.dump_json(replace(self, records=(), schemas=())).decode("utf-8")

    @classmethod
    def from_snapshot_json(cls, contents: str) -> CollectionScan:
        """Read a snapshot produced by the Python API from a trusted local cache."""
        # The public views are rebuilt from authoritative cached inputs and verdicts.
        result = _SNAPSHOT.validate_json(contents)
        if result._version != _SNAPSHOT_VERSION:
            raise ValueError("unsupported collection snapshot version")
        return result._with_public_views()

    def _with_public_views(self) -> CollectionScan:
        return replace(
            self,
            records=deepcopy(self._bound_records),
            schemas=deepcopy(tuple(entry.schema for entry in self._files.values() if entry.schema)),
        )

    def summary(self) -> dict[str, Any]:
        """Report verdicts and counts without exposing payload or body values."""
        contracts: Counter[str] = Counter()
        states: Counter[str] = Counter()
        problems = list(self.problems)
        for record in self.records:
            states[record.state] += 1
            if record.metadata is not None:
                contracts[record.metadata.contract_id] += 1
            problems.extend(
                {"path": record.path, "code": str(error.get("code", error.get("kind", "invalid")))}
                for error in record.errors
            )
        return {
            "complete": self.complete,
            "contracts": dict(contracts),
            "states": dict(states),
            "schemas": len(self.schemas),
            "problems": sorted(problems, key=lambda problem: (problem["path"], problem["code"])),
        }


_SNAPSHOT = TypeAdapter(CollectionScan)


def _fingerprint(status: os.stat_result) -> tuple[int, ...]:
    return (status.st_dev, status.st_ino, status.st_size, status.st_mtime_ns, status.st_ctime_ns)


def _read(path: Path, status: os.stat_result, limit: int) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or _fingerprint(status) != _fingerprint(before):
            raise OSError("file changed during scan")
        data = stream.read(limit + 1)
        if len(data) > limit or _fingerprint(before) != _fingerprint(os.fstat(stream.fileno())):
            raise OSError("file changed during scan")
    return data.decode("utf-8-sig")


def _walk(
    root: Path,
    max_entries: int,
    ignore: Callable[[str, bool], bool] | None,
    problems: list[dict[str, str]],
) -> tuple[list[tuple[str, os.stat_result]], bool]:
    files: list[tuple[str, os.stat_result]] = []
    directories = [root]
    walked = 0
    while directories:
        directory = directories.pop()
        try:
            if directory.resolve(strict=True) != directory:
                raise OSError("directory changed during scan")
            with os.scandir(directory) as listing:
                entries = []
                for entry in listing:
                    walked += 1
                    if walked > max_entries:
                        problems.append(
                            {"path": directory.relative_to(root).as_posix(), "code": "entry_limit"}
                        )
                        return sorted(files), False
                    entries.append(entry)
                for entry in sorted(entries, key=lambda entry: entry.name, reverse=True):
                    if entry.name.startswith(".") or entry.is_symlink():
                        continue
                    path = Path(entry.path)
                    relative = path.relative_to(root).as_posix()
                    try:
                        is_directory = entry.is_dir(follow_symlinks=False)
                        if ignore is not None and ignore(relative, is_directory):
                            continue
                        if is_directory:
                            directories.append(path)
                        elif path.suffix.lower() in _ARTIFACT_SUFFIXES and entry.is_file(
                            follow_symlinks=False
                        ):
                            files.append((relative, entry.stat(follow_symlinks=False)))
                    except OSError:
                        problems.append({"path": relative, "code": "entry_unreadable"})
        except OSError as error:
            if directory == root:
                raise ValueError("collection root cannot be opened") from error
            problems.append(
                {"path": directory.relative_to(root).as_posix(), "code": "directory_unreadable"}
            )
    return sorted(files), not problems


def _read_record(path: str, text: str) -> tuple[CollectionRecord | None, str]:
    yaml_named = path.lower().endswith((".yaml", ".yml"))
    fenced = not yaml_named and opens_frontmatter_fence(text)
    profile = SchemaProfile.frontmatter_md if fenced else SchemaProfile.pure_yaml
    split = split_frontmatter(text) if profile is SchemaProfile.frontmatter_md else None
    yaml = split.metadata_text if split is not None else text
    # A key may contain escapes, so that possibility also requires the portable reader.
    if "softschema" not in yaml and "\\" not in yaml:
        return None, ""
    body = text[split.body_offset :] if split is not None else ""
    repairs: tuple[dict[str, Any], ...] = ()
    try:
        if profile is SchemaProfile.frontmatter_md:
            _, document = parse_frontmatter_text(text, source=path)
        else:
            document = parse_yaml_text(text, source=path)
    except PortableInputError:
        if not fenced and path.lower().endswith(".md"):
            return None, ""
        if profile is SchemaProfile.frontmatter_md and split is None:
            return CollectionRecord(
                path, profile, "unreadable", errors=({"kind": "yaml_parse_error"},)
            ), ""
        repaired = repair_yaml_text(yaml.replace("\r\n", "\n"))
        if not repaired.ok or repaired.text is None:
            return CollectionRecord(
                path, profile, "unreadable", errors=({"kind": "yaml_parse_error"},)
            ), ""
        yaml = repaired.text
        document = parse_yaml_text(yaml, source=path)
        repairs = tuple(repaired.records)
    if not isinstance(document, dict) or "softschema" not in document:
        return None, ""
    try:
        metadata = parse_schema_metadata(document["softschema"])
    except ValueError:
        metadata = None
    if metadata is None:
        return CollectionRecord(
            path, profile, "malformed", errors=({"kind": "document_softschema_invalid"},)
        ), ""
    # The artifact layer resolves envelopes. Remove the untrusted schema pointer here
    # and bind after discovery, exclusively through the scanned schemas.
    declaration = metadata.model_dump(by_alias=True, exclude={"schema_ref"}, exclude_none=True)
    contract = Contract(
        id=metadata.contract_id, profile=profile, status=metadata.status or SchemaStatus.soft
    )
    extracted = validate_artifact(
        Path(path),
        contract=contract,
        document={
            **document,
            "softschema": declaration,
        },
    )
    if extracted.values is None:
        return CollectionRecord(
            path, profile, "malformed", metadata, errors=tuple(extracted.structural.errors)
        ), ""
    envelope = metadata.envelope
    if envelope is None and profile is SchemaProfile.frontmatter_md:
        envelope = infer_envelope_key(document)
    host = (
        {
            key: value
            for key, value in document.items()
            if key != "softschema" and key != metadata.envelope
        }
        if metadata.envelope is not None
        else {}
    )
    return CollectionRecord(
        path,
        profile,
        "unbound",
        metadata,
        extracted.values,
        host,
        body,
        repairs=repairs,
        envelope=envelope,
    ), yaml


def _pointer(record: CollectionRecord) -> str | None:
    ref = record.metadata.schema_ref if record.metadata is not None else None
    if ref is None or "\\" in ref or Path(ref).is_absolute() or PureWindowsPath(ref).drive:
        return None
    relative = os.path.normpath((Path(record.path).parent / ref).as_posix()).replace(os.sep, "/")
    return relative if relative != ".." and not relative.startswith("../") else None


def _bind(
    record: CollectionRecord,
    record_yaml: str,
    schemas: dict[str, tuple[CollectionSchema, str]],
    by_contract: dict[str, dict[str, str]],
    complete: bool,
    prior: tuple[CollectionRecord, str | None] | None,
) -> CollectionRecord:
    if record.metadata is None or record.values is None:
        return record
    contract = record.metadata.contract_id
    pointer = _pointer(record)
    direct = schemas.get(pointer or "")
    if direct is None or direct[0].contract not in (None, contract):
        candidates = by_contract.get(contract, {})
        if not complete or len(candidates) != 1:
            code = (
                "schema_ambiguous"
                if len(candidates) > 1
                else ("schema_unbound" if complete else "schema_discovery_incomplete")
            )
            return replace(record, errors=({"kind": code},))
        direct = schemas[next(iter(candidates.values()))]
    schema, text = direct
    if prior is not None and (prior[0].schema, prior[1]) == (schema.path, schema.digest):
        return prior[0]
    strict = record.metadata.status is SchemaStatus.enforced

    path = Path(schema.path)
    verdict = validate_structural_text(record.values, text, path, strict_extras=strict)
    if verdict.execution == "completed" and not verdict.ok and record_yaml:

        def check_conformance(values: dict[str, Any]) -> StructuralResult:
            payload = _without_metadata(values) if record.envelope is None else values
            return validate_structural_text(payload, text, path)

        conformed = _conform_text(
            record_yaml,
            check_conformance,
            None,
            record.envelope,
            SchemaProfile.pure_yaml,
        )
        if conformed.changed and conformed.text is not None:
            updated = parse_yaml_text(conformed.text, source=record.path)
            if isinstance(updated, dict):
                values = (
                    updated.get(record.envelope) if record.envelope else _without_metadata(updated)
                )
                if isinstance(values, dict):
                    final = validate_structural_text(values, text, path, strict_extras=strict)
                    if final.execution == "completed" and final.ok:
                        return replace(
                            record,
                            state="repaired",
                            schema=schema.path,
                            values=values,
                            repairs=(*record.repairs, *conformed.records),
                            execution=final.execution,
                        )
    state: RecordState = "unbound"
    if verdict.execution == "completed":
        state = ("repaired" if record.repairs else "valid") if verdict.ok else "invalid"
    return replace(
        record,
        state=state,
        schema=schema.path,
        errors=tuple(verdict.errors),
        execution=verdict.execution,
    )


def _without_metadata(document: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in document.items() if key != "softschema"}


def _valid_bound(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 < value <= MAX_SAFE_INTEGER


def _scan_file(relative: str, stamp: tuple[int, ...], data: str) -> _ScannedFile:
    if not relative.lower().endswith(_SCHEMA_SUFFIXES):
        record, yaml = _read_record(relative, data)
        return _ScannedFile(stamp, record=record, record_yaml=yaml)
    try:
        schema_root = parse_yaml_text(data, source=relative)
        if not isinstance(schema_root, dict):
            raise ValueError("schema root must be a mapping")
        document = cast(dict[str, Any], schema_root)
        contract_id = SchemaView(document).contract_id
        digest = _schema_sha256(document)
    except (TypeError, ValueError):
        return _ScannedFile(stamp, problem="schema_invalid")
    schema = CollectionSchema(relative, digest, contract_id, document)
    return _ScannedFile(stamp, schema=schema, schema_text=data)


def scan_collection(
    root: Path,
    *,
    max_entries: int = 50_000,
    max_file_bytes: int = 1024 * 1024,
    max_total_bytes: int = 64 * 1024 * 1024,
    ignore: Callable[[str, bool], bool] | None = None,
    previous: CollectionScan | None = None,
    ignore_id: str | None = None,
) -> CollectionScan:
    """Scan regular files under one root, leaving sources untouched.

    Paths in the result and in the optional ignore callback are relative to the root.
    The entry bound covers every enumerated name. The file and aggregate read bounds
    limit memory and work independently. When a bound cuts the scan, `complete` is false.
    A fully walked listing can establish removals even when record reads hit a byte limit.
    A partial scan binds an observed explicit schema pointer, and defers unique-contract
    fallback until discovery completes.
    A previous scan with the same root, limits and ignore identity can reuse unchanged
    artifacts. Pass a stable `ignore_id` for the effective policy when providing an
    ignore callback. A scan without that identity does a fresh read.
    """
    if not all(map(_valid_bound, (max_entries, max_file_bytes, max_total_bytes))):
        raise ValueError("collection bounds must be positive safe integers")
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("collection root must be a directory")
    scope = (str(root), ignore is not None, ignore_id, max_entries, max_file_bytes, max_total_bytes)
    if previous is not None and (
        previous._version != _SNAPSHOT_VERSION
        or previous._scope != scope
        or (ignore is not None and ignore_id is None)
    ):
        previous = None
    saved_files = previous._files if previous is not None else {}
    known_stamps = previous._known_stamps if previous else {}
    prior_records = {record.path: record for record in previous._bound_records} if previous else {}
    problems: list[dict[str, str]] = []
    files, walked = _walk(root, max_entries, ignore, problems)
    complete = walked
    records: list[CollectionRecord] = []
    scanned: dict[str, _ScannedFile] = {}
    schemas: dict[str, tuple[CollectionSchema, str]] = {}
    by_contract: dict[str, dict[str, str]] = defaultdict(dict)
    remaining = max_total_bytes
    for relative, status in files:
        if status.st_size > max_file_bytes:
            problems.append({"path": relative, "code": "file_too_large"})
            complete = False
            continue
        if status.st_size > remaining:
            problems.append({"path": relative, "code": "total_byte_limit"})
            complete = False
            break
        remaining -= status.st_size
        stamp = _fingerprint(status)
        entry = saved_files.get(relative)
        if entry is None or entry.stamp != stamp:
            path = root / relative
            try:
                if path.resolve(strict=True) != path:
                    raise OSError("file changed during scan")
                data = _read(path, status, status.st_size)
            except (OSError, UnicodeError):
                problems.append({"path": relative, "code": "file_unreadable"})
                complete = False
                continue
            entry = _scan_file(relative, stamp, data)
        scanned[relative] = entry
        if entry.problem is not None:
            problems.append({"path": relative, "code": entry.problem})
        if entry.schema is not None and entry.schema_text is not None:
            schemas[relative] = (entry.schema, entry.schema_text)
            if entry.schema.contract is not None:
                by_contract[entry.schema.contract].setdefault(entry.schema.digest, relative)
        if entry.record is not None:
            records.append(entry.record)

    def bind(record: CollectionRecord) -> CollectionRecord:
        prior = prior_records.get(record.path)
        latest = scanned[record.path]
        if latest is saved_files.get(record.path) and prior is not None:
            old_schema = saved_files.get(prior.schema or "")
            old_digest = old_schema.schema.digest if old_schema and old_schema.schema else None
            return _bind(
                record,
                latest.record_yaml,
                schemas,
                by_contract,
                complete,
                (prior, old_digest),
            )
        return _bind(record, latest.record_yaml, schemas, by_contract, complete, None)

    # Only a complete listing can advance membership. Byte limits can leave known
    # files unread without making them disappear.
    listed = {name for name, _ in files}
    removed = known_stamps.keys() - listed if walked else set()
    added = tuple(name for name in scanned if name not in known_stamps) if walked else ()
    next_known = {name: stamp for name, stamp in known_stamps.items() if name not in removed}
    next_known.update(
        {name: entry.stamp for name, entry in scanned.items() if walked or name in next_known}
    )
    return CollectionScan(
        (),
        (),
        tuple(problems),
        complete,
        added,
        tuple(
            name
            for name in scanned
            if name in known_stamps and scanned[name].stamp != known_stamps[name]
        ),
        tuple(sorted(removed)),
        _SNAPSHOT_VERSION,
        scope,
        scanned,
        next_known,
        tuple(bind(record) for record in records),
    )._with_public_views()
