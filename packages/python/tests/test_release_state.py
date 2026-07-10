"""Release-state classifiers and privileged workflow orchestration tests."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from devtools import release_state
from devtools.release_state import (
    CONTROL_FILES,
    MAX_RELEASE_SUBJECT_BYTES,
    MAX_RELEASE_TOTAL_BYTES,
    NPM_PROVENANCE_PREDICATE,
    NPM_SOURCE_REPOSITORY,
    NPM_SOURCE_WORKFLOW,
    PRIMARY_CHECKSUMS_NAME,
    PYPI_TRUSTED_PUBLISHER,
    RELEASE_INDEX_NAME,
    RELEASE_MANIFEST_NAME,
    ReleaseStateError,
    check_npm_audit_attestations,
    check_pypi_integrity_metadata,
    classify_github,
    classify_github_latest,
    classify_npm,
    classify_pypi,
    expected_github_assets,
    extract_recovery_bundle,
    load_manifest,
    release_coordinates,
    stage_npm_signature_consumer,
    stage_pypi,
    write_controls,
    write_recovery_bundle,
)

ROOT = Path(__file__).parents[3]


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha512_integrity(value: bytes) -> str:
    digest = base64.b64encode(hashlib.sha512(value).digest()).decode("ascii")
    return f"sha512-{digest}"


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _write_recovery_archive(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, mode="w:", format=tarfile.PAX_FORMAT) as archive:
        for name, value in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(value)
            archive.addfile(info, io.BytesIO(value))


def _der(tag: int, *values: bytes) -> bytes:
    value = b"".join(values)
    if len(value) < 0x80:
        length = bytes([len(value)])
    else:
        encoded = len(value).to_bytes((len(value).bit_length() + 7) // 8)
        length = bytes([0x80 | len(encoded)]) + encoded
    return bytes([tag]) + length + value


def _test_certificate(*identities: str) -> bytes:
    algorithm = _der(0x30, _der(0x06, b"\x2a\x86\x48\x86\xf7\x0d\x01\x01\x0b"), _der(0x05))
    name = _der(0x30)
    validity = _der(
        0x30,
        _der(0x17, b"260101000000Z"),
        _der(0x17, b"270101000000Z"),
    )
    subject_public_key = _der(0x30, algorithm, _der(0x03, b"\x00\x00"))
    general_names = _der(0x30, *(_der(0x86, identity.encode("ascii")) for identity in identities))
    subject_alt_name = _der(
        0x30,
        _der(0x06, b"\x55\x1d\x11"),
        _der(0x04, general_names),
    )
    extensions = _der(0xA3, _der(0x30, subject_alt_name))
    tbs = _der(
        0x30,
        _der(0xA0, _der(0x02, b"\x02")),
        _der(0x02, b"\x01"),
        algorithm,
        name,
        validity,
        name,
        subject_public_key,
        extensions,
    )
    return _der(0x30, tbs, algorithm, _der(0x03, b"\x00\x00"))


def _candidate(tmp_path: Path, logical_version: str = "0.3.0") -> tuple[Path, dict[str, bytes]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    python_version = logical_version.replace("-rc.", "rc")
    values = {
        f"softschema-{python_version}-py3-none-any.whl": b"wheel",
        f"softschema-{python_version}.tar.gz": b"sdist",
        f"softschema-{logical_version}.tgz": b"npm",
        "conformance-kit.tar.gz": b"conformance",
        "release-metadata.json": b"{}\n",
        "build-metadata.json": b"{}\n",
        "softschema-python-wheel.spdx.json": b"{}\n",
        "softschema-python-sdist.spdx.json": b"{}\n",
        "softschema-npm.spdx.json": b"{}\n",
    }
    kinds = {
        "conformance-kit.tar.gz": "conformance",
        "release-metadata.json": "release_metadata",
        "build-metadata.json": "build_metadata",
    }
    subjects: dict[str, dict[str, Any]] = {}
    for name, value in values.items():
        (tmp_path / name).write_bytes(value)
        if name in kinds:
            kind = kinds[name]
        elif name.endswith(".whl"):
            kind = "wheel"
        elif name.endswith(".tar.gz"):
            kind = "sdist"
        elif name.endswith(".tgz"):
            kind = "npm"
        else:
            kind = "sbom"
        subjects[name] = {
            "kind": kind,
            "media_type": "application/octet-stream",
            "size": len(value),
            "sha256": _sha256(value),
        }
    manifest = {
        "schema_version": "1",
        "logical_version": logical_version,
        "source_commit": "a" * 40,
        "subjects": subjects,
    }
    (tmp_path / RELEASE_MANIFEST_NAME).write_bytes(_canonical_json(manifest))
    return tmp_path, values


def _pypi_payload(directory: Path, names: list[str]) -> dict[str, Any]:
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    return {
        "info": {"version": manifest.coordinates.python_version},
        "urls": [
            {
                "filename": name,
                "digests": {"sha256": manifest.subjects[name].sha256},
                "size": manifest.subjects[name].size,
                "yanked": False,
            }
            for name in names
        ],
    }


def _npm_payload(directory: Path, npm_bytes: bytes) -> dict[str, Any]:
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    subject = manifest.one("npm")
    return {
        "name": "softschema",
        "version": manifest.coordinates.npm_version,
        "dist": {
            "integrity": _sha512_integrity(npm_bytes),
            "shasum": hashlib.sha1(npm_bytes, usedforsecurity=False).hexdigest(),
            "tarball": f"https://registry.npmjs.org/softschema/-/{subject.name}",
        },
    }


def _github_payload(directory: Path, *, draft: bool = True) -> dict[str, Any]:
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    assets = expected_github_assets(directory, manifest)
    return {
        "tag_name": f"v{manifest.logical_version}",
        "draft": draft,
        "immutable": not draft,
        "prerelease": manifest.coordinates.prerelease,
        "assets": [
            {
                "name": name,
                "state": "uploaded",
                "size": item.size,
                "digest": f"sha256:{item.sha256}",
                "id": index,
                "url": f"https://api.github.com/repos/jlevy/softschema/releases/assets/{index}",
            }
            for index, (name, item) in enumerate(assets.items(), start=1)
        ],
    }


def _pypi_integrity_payloads(directory: Path) -> dict[str, Any]:
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    fixtures: dict[str, Any] = {}
    for subject in manifest.by_kind("wheel", "sdist"):
        statement = {
            "_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": subject.name, "digest": {"sha256": subject.sha256}}],
            "predicateType": "https://docs.pypi.org/attestations/publish/v1",
            "predicate": None,
        }
        fixtures[subject.name] = {
            "version": 1,
            "attestation_bundles": [
                {
                    "publisher": {**PYPI_TRUSTED_PUBLISHER, "claims": None},
                    "attestations": [
                        {
                            "envelope": {
                                "statement": base64.b64encode(_canonical_json(statement)).decode()
                            }
                        }
                    ],
                }
            ],
        }
    return fixtures


def _npm_audit_report(
    directory: Path,
    npm_bytes: bytes,
    *,
    repository: str = NPM_SOURCE_REPOSITORY,
    certificate_identity: str | None = None,
) -> dict[str, Any]:
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    version = manifest.coordinates.npm_version
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {
                "name": f"pkg:npm/softschema@{version}",
                "digest": {"sha512": hashlib.sha512(npm_bytes).hexdigest()},
            }
        ],
        "predicateType": NPM_PROVENANCE_PREDICATE,
        "predicate": {
            "buildDefinition": {
                "externalParameters": {
                    "workflow": {
                        "repository": repository,
                        "path": NPM_SOURCE_WORKFLOW,
                        "ref": f"refs/tags/v{manifest.logical_version}",
                    }
                }
            }
        },
    }
    identity = certificate_identity or (
        f"{NPM_SOURCE_REPOSITORY}/{NPM_SOURCE_WORKFLOW}@refs/tags/v{manifest.logical_version}"
    )
    return {
        "invalid": [],
        "missing": [],
        "verified": [
            {
                "name": "softschema",
                "version": version,
                "attestationBundles": [
                    {
                        "predicateType": NPM_PROVENANCE_PREDICATE,
                        "bundle": {
                            "verificationMaterial": {
                                "certificate": {
                                    "rawBytes": base64.b64encode(
                                        _test_certificate(identity)
                                    ).decode()
                                }
                            },
                            "dsseEnvelope": {
                                "payload": base64.b64encode(_canonical_json(statement)).decode()
                            },
                        },
                    }
                ],
            }
        ],
    }


def test_controls_are_deterministic_and_have_no_digest_cycle(tmp_path: Path) -> None:
    directory, _ = _candidate(tmp_path)
    first = write_controls(directory)
    primary = (directory / PRIMARY_CHECKSUMS_NAME).read_text(encoding="utf-8")
    index_bytes = (directory / RELEASE_INDEX_NAME).read_bytes()
    second = write_controls(directory)

    assert first == second
    assert (directory / RELEASE_INDEX_NAME).read_bytes() == index_bytes
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    assert primary == "".join(
        f"{manifest.subjects[name].sha256}  {name}\n" for name in sorted(manifest.subjects)
    )
    index = json.loads(index_bytes)
    assert index["release_manifest"]["sha256"] == _sha256(
        (directory / RELEASE_MANIFEST_NAME).read_bytes()
    )
    assert index["primary_checksums"]["sha256"] == _sha256(primary.encode())
    assert index["control_files"] == list(CONTROL_FILES)
    assert RELEASE_INDEX_NAME not in index["release_manifest"]
    assert "sha256" not in index.get("release_index", {})


def test_release_control_rejects_a_huge_sparse_file_before_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory, _ = _candidate(tmp_path)
    write_controls(directory)
    control = directory / PRIMARY_CHECKSUMS_NAME
    with control.open("wb") as stream:
        stream.truncate(MAX_RELEASE_SUBJECT_BYTES + 1)

    def reject_unbounded_read(_path: Path) -> bytes:
        pytest.fail("release controls must not use Path.read_bytes()")

    monkeypatch.setattr(Path, "read_bytes", reject_unbounded_read)
    with pytest.raises(ReleaseStateError, match=r"release input exceeds the \d+-byte limit"):
        expected_github_assets(directory)


def test_manifest_loader_rejects_duplicate_keys_and_wrong_package_names(tmp_path: Path) -> None:
    path = tmp_path / RELEASE_MANIFEST_NAME
    path.write_text('{"schema_version":"1","schema_version":"1"}\n', encoding="utf-8")
    with pytest.raises(ReleaseStateError, match="duplicate JSON key"):
        load_manifest(path)

    directory, _ = _candidate(tmp_path / "candidate")
    payload = json.loads((directory / RELEASE_MANIFEST_NAME).read_text(encoding="utf-8"))
    wheel = next(name for name, item in payload["subjects"].items() if item["kind"] == "wheel")
    payload["subjects"]["other.whl"] = payload["subjects"].pop(wheel)
    (directory / RELEASE_MANIFEST_NAME).write_bytes(_canonical_json(payload))
    with pytest.raises(ReleaseStateError, match="wheel filename"):
        load_manifest(directory / RELEASE_MANIFEST_NAME)

    reserved_directory, _ = _candidate(tmp_path / "reserved")
    reserved = json.loads((reserved_directory / RELEASE_MANIFEST_NAME).read_text(encoding="utf-8"))
    sbom = next(name for name, item in reserved["subjects"].items() if item["kind"] == "sbom")
    reserved["subjects"][RELEASE_INDEX_NAME] = reserved["subjects"].pop(sbom)
    (reserved_directory / RELEASE_MANIFEST_NAME).write_bytes(_canonical_json(reserved))
    with pytest.raises(ReleaseStateError, match="collides with a control filename"):
        load_manifest(reserved_directory / RELEASE_MANIFEST_NAME)


def test_manifest_loader_bounds_each_subject_and_the_aggregate_before_reads(
    tmp_path: Path,
) -> None:
    directory, _ = _candidate(tmp_path / "per-subject")
    manifest_path = directory / RELEASE_MANIFEST_NAME
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    first = next(iter(payload["subjects"].values()))
    first["size"] = MAX_RELEASE_SUBJECT_BYTES + 1
    manifest_path.write_bytes(_canonical_json(payload))
    with pytest.raises(ReleaseStateError, match="subject byte limit"):
        load_manifest(manifest_path)

    directory, _ = _candidate(tmp_path / "aggregate")
    manifest_path = directory / RELEASE_MANIFEST_NAME
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    subject_sizes = [MAX_RELEASE_SUBJECT_BYTES, MAX_RELEASE_SUBJECT_BYTES, 1]
    for subject, size in zip(list(payload["subjects"].values())[:3], subject_sizes, strict=True):
        subject["size"] = size
    assert sum(subject_sizes) > MAX_RELEASE_TOTAL_BYTES
    manifest_path.write_bytes(_canonical_json(payload))
    with pytest.raises(ReleaseStateError, match="aggregate subject byte limit"):
        load_manifest(manifest_path)


def test_manifest_schema_and_runtime_share_declared_byte_limits(tmp_path: Path) -> None:
    schema = json.loads(
        (ROOT / "conformance/schemas/release-manifest.schema.json").read_text(encoding="utf-8")
    )
    subjects_schema = schema["properties"]["subjects"]
    size_schema = schema["$defs"]["subject"]["properties"]["size"]
    assert size_schema["maximum"] == MAX_RELEASE_SUBJECT_BYTES
    assert str(MAX_RELEASE_TOTAL_BYTES) in subjects_schema["description"]

    directory, _ = _candidate(tmp_path / "candidate")
    manifest_path = directory / RELEASE_MANIFEST_NAME
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    first = next(iter(payload["subjects"].values()))
    first["size"] = MAX_RELEASE_SUBJECT_BYTES
    validator = Draft202012Validator(schema)
    assert validator.is_valid(payload)
    manifest_path.write_bytes(_canonical_json(payload))
    assert load_manifest(manifest_path).subjects

    first["size"] = MAX_RELEASE_SUBJECT_BYTES + 1
    assert not validator.is_valid(payload)
    manifest_path.write_bytes(_canonical_json(payload))
    with pytest.raises(ReleaseStateError, match="subject byte limit"):
        load_manifest(manifest_path)


@pytest.mark.parametrize(
    "payload",
    [
        b'{"value":"\\ud800"}',
        b'{"\\udfff":true}',
        b'{"value":1e999}',
        ("[" * 1200 + "]" * 1200).encode(),
        ('{"value":' + "9" * 5000 + "}").encode(),
    ],
)
def test_release_json_rejects_nonportable_or_unbounded_values(payload: bytes) -> None:
    with pytest.raises(ReleaseStateError, match=r"(?:JSON|non-finite)"):
        release_state._loads_json(payload, "release fixture")


def test_release_json_read_enforces_limit_after_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "growing.json"
    path.write_bytes(b" " * (release_state.MAX_JSON_BYTES + 1))
    real_stat = Path.stat

    def stale_stat(candidate: Path, *args: object, **kwargs: object) -> os.stat_result:
        result = real_stat(candidate, *args, **kwargs)
        if candidate == path:
            values = list(result)
            values[6] = 1
            return os.stat_result(values)
        return result

    monkeypatch.setattr(Path, "stat", stale_stat)
    with pytest.raises(ReleaseStateError, match=r"exceeds the \d+-byte limit"):
        release_state._read_json(path)


def test_release_json_rejects_replacement_between_inspection_and_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "fixture.json"
    replacement = tmp_path / "replacement.json"
    displaced = tmp_path / "displaced.json"
    path.write_bytes(b'{"safe":true}')
    replacement.write_bytes(b'{"evil":true}')
    real_open = os.open
    replaced = False

    def replace_then_open(candidate: os.PathLike[str], flags: int) -> int:
        nonlocal replaced
        if Path(candidate) == path and not replaced:
            replaced = True
            path.replace(displaced)
            replacement.replace(path)
        return real_open(candidate, flags)

    monkeypatch.setattr(os, "open", replace_then_open)
    with pytest.raises(ReleaseStateError, match="JSON fixture changed while opening"):
        release_state._read_json(path)
    assert replaced


def test_release_regular_bytes_rejects_replacement_between_inspection_and_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "subject.bin"
    replacement = tmp_path / "replacement.bin"
    displaced = tmp_path / "displaced.bin"
    path.write_bytes(b"safe")
    replacement.write_bytes(b"evil")
    real_open = os.open
    replaced = False

    def replace_then_open(candidate: os.PathLike[str], flags: int) -> int:
        nonlocal replaced
        if Path(candidate) == path and not replaced:
            replaced = True
            path.replace(displaced)
            replacement.replace(path)
        return real_open(candidate, flags)

    monkeypatch.setattr(os, "open", replace_then_open)
    with pytest.raises(ReleaseStateError, match="changed while opening"):
        release_state._regular_bytes(path, limit=4, expected_size=4)


def test_release_regular_bytes_rejects_growth_after_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "subject.bin"
    path.write_bytes(b"safe")
    real_read = os.read
    grew = False

    def grow_after_first_read(descriptor: int, count: int) -> bytes:
        nonlocal grew
        chunk = real_read(descriptor, min(count, 2))
        if chunk and not grew:
            grew = True
            with path.open("ab") as stream:
                stream.write(b"!")
        return chunk

    monkeypatch.setattr(os, "read", grow_after_first_read)
    with pytest.raises(ReleaseStateError, match="exceeds the 4-byte limit"):
        release_state._regular_bytes(path, limit=4, expected_size=4)


def test_release_hash_rejects_replacement_between_inspection_and_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "subject.bin"
    replacement = tmp_path / "replacement.bin"
    displaced = tmp_path / "displaced.bin"
    path.write_bytes(b"safe")
    replacement.write_bytes(b"evil")
    real_open = os.open
    replaced = False

    def replace_then_open(candidate: os.PathLike[str], flags: int) -> int:
        nonlocal replaced
        if Path(candidate) == path and not replaced:
            replaced = True
            path.replace(displaced)
            replacement.replace(path)
        return real_open(candidate, flags)

    monkeypatch.setattr(os, "open", replace_then_open)
    with pytest.raises(ReleaseStateError, match="release input changed while opening"):
        release_state._sha256_regular_file(path, limit=4, expected_size=4)
    assert replaced


def test_release_hash_rejects_growth_after_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "subject.bin"
    path.write_bytes(b"safe")
    real_read = os.read
    grew = False

    def grow_after_first_read(descriptor: int, count: int) -> bytes:
        nonlocal grew
        chunk = real_read(descriptor, min(count, 2))
        if chunk and not grew:
            grew = True
            with path.open("ab") as stream:
                stream.write(b"!")
        return chunk

    monkeypatch.setattr(os, "read", grow_after_first_read)
    with pytest.raises(ReleaseStateError, match="exceeds the 4-byte limit"):
        release_state._sha256_regular_file(path, limit=4, expected_size=4)
    assert grew


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="platform has no FIFO support")
def test_release_hash_rejects_special_nodes_without_opening(tmp_path: Path) -> None:
    path = tmp_path / "subject.pipe"
    os.mkfifo(path)

    with pytest.raises(ReleaseStateError, match="release input must be a regular file"):
        release_state._sha256_regular_file(path, limit=1)


def test_pypi_state_machine_covers_absent_partial_complete_and_conflict(tmp_path: Path) -> None:
    directory, _ = _candidate(tmp_path)
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    package_names = sorted(item.name for item in manifest.by_kind("wheel", "sdist"))

    absent = classify_pypi(manifest, None)
    assert absent.state == "absent"
    assert absent.missing == tuple(package_names)

    partial = classify_pypi(manifest, _pypi_payload(directory, package_names[:1]))
    assert partial.state == "partial"
    assert partial.exact == (package_names[0],)
    assert partial.missing == (package_names[1],)

    reverse = classify_pypi(manifest, _pypi_payload(directory, package_names[1:]))
    assert reverse.state == "partial"
    assert reverse.exact == (package_names[1],)
    assert reverse.missing == (package_names[0],)

    complete = classify_pypi(manifest, _pypi_payload(directory, package_names))
    assert complete.state == "complete"
    assert complete.missing == ()

    unknown = _pypi_payload(directory, package_names)
    unknown["urls"].append({"filename": "unknown.whl", "digests": {"sha256": "0" * 64}})
    decision = classify_pypi(manifest, unknown)
    assert decision.state == "conflict"
    assert {problem.code for problem in decision.problems} == {"unexpected_filename"}

    mismatch = _pypi_payload(directory, package_names)
    mismatch["urls"][0]["digests"]["sha256"] = "0" * 64
    decision = classify_pypi(manifest, mismatch)
    assert decision.state == "conflict"
    assert {problem.code for problem in decision.problems} == {"digest_mismatch"}

    duplicate = _pypi_payload(directory, package_names)
    duplicate_record = dict(duplicate["urls"][0])
    duplicate_record["digests"] = {"sha256": "0" * 64}
    duplicate["urls"].append(duplicate_record)
    forward = classify_pypi(manifest, duplicate).to_dict()
    duplicate["urls"].reverse()
    assert classify_pypi(manifest, duplicate).to_dict() == forward
    assert "duplicate_filename" in {problem["code"] for problem in forward["problems"]}


@pytest.mark.parametrize(
    ("field", "value", "problem"),
    [
        ("yanked", True, "yanked_file"),
        ("yanked", "false", "invalid_yanked"),
        ("size", 999, "size_mismatch"),
        ("size", True, "invalid_size"),
    ],
)
def test_pypi_rejects_yanked_or_size_conflicts(
    tmp_path: Path,
    field: str,
    value: Any,
    problem: str,
) -> None:
    directory, _ = _candidate(tmp_path)
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    package_names = sorted(item.name for item in manifest.by_kind("wheel", "sdist"))
    payload = _pypi_payload(directory, package_names)
    payload["urls"][0][field] = value

    decision = classify_pypi(manifest, payload)

    assert decision.state == "conflict"
    assert problem in {item.code for item in decision.problems}


def test_pypi_partial_staging_copies_only_missing_exact_subjects(tmp_path: Path) -> None:
    directory, _ = _candidate(tmp_path / "candidate")
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    names = sorted(item.name for item in manifest.by_kind("wheel", "sdist"))
    decision = classify_pypi(manifest, _pypi_payload(directory, names[:1]))
    plan = tmp_path / "plan.json"
    plan.write_bytes(_canonical_json(decision.to_dict()))
    output = tmp_path / "pypi"

    stage_pypi(directory, plan, output)

    assert sorted(path.name for path in output.iterdir()) == [names[1]]


def test_npm_state_machine_verifies_tarball_digest_integrity_and_channel(tmp_path: Path) -> None:
    directory, values = _candidate(tmp_path)
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    npm_name = manifest.one("npm").name
    npm_bytes = values[npm_name]

    assert classify_npm(manifest, None, None).state == "absent"
    exact = classify_npm(manifest, _npm_payload(directory, npm_bytes), npm_bytes)
    assert exact.state == "complete"

    mismatch = classify_npm(manifest, _npm_payload(directory, npm_bytes), b"different")
    assert mismatch.state == "conflict"
    assert "digest_mismatch" in {problem.code for problem in mismatch.problems}

    bad_integrity = _npm_payload(directory, npm_bytes)
    bad_integrity["dist"]["integrity"] = "sha512-AAAA"
    decision = classify_npm(manifest, bad_integrity, npm_bytes)
    assert decision.state == "conflict"
    assert "integrity_mismatch" in {problem.code for problem in decision.problems}

    packument = {"dist-tags": {"latest": manifest.coordinates.npm_version}}
    assert (
        classify_npm(
            manifest,
            _npm_payload(directory, npm_bytes),
            npm_bytes,
            packument=packument,
            require_channel=True,
        ).state
        == "complete"
    )
    packument["dist-tags"]["latest"] = "0.2.2"
    assert (
        classify_npm(
            manifest,
            _npm_payload(directory, npm_bytes),
            npm_bytes,
            packument=packument,
            require_channel=True,
        ).state
        == "conflict"
    )

    rc_directory, rc_values = _candidate(tmp_path / "rc", "0.3.0-rc.2")
    rc_manifest = load_manifest(rc_directory / RELEASE_MANIFEST_NAME)
    rc_name = rc_manifest.one("npm").name
    assert (
        classify_npm(
            rc_manifest,
            _npm_payload(rc_directory, rc_values[rc_name]),
            rc_values[rc_name],
            packument={"dist-tags": {"next": "0.3.0-rc.2", "latest": "0.2.2"}},
            require_channel=True,
        ).state
        == "complete"
    )
    prerelease_latest = classify_npm(
        rc_manifest,
        _npm_payload(rc_directory, rc_values[rc_name]),
        rc_values[rc_name],
        packument={"dist-tags": {"next": "0.3.0-rc.2", "latest": "0.3.0-rc.2"}},
        require_channel=True,
    )
    assert prerelease_latest.state == "conflict"
    assert "prerelease_is_latest" in {problem.code for problem in prerelease_latest.problems}


def test_release_coordinates_fix_stable_and_prerelease_channels() -> None:
    stable = release_coordinates("0.3.0")
    assert (stable.python_version, stable.npm_version, stable.npm_tag, stable.prerelease) == (
        "0.3.0",
        "0.3.0",
        "latest",
        False,
    )
    candidate = release_coordinates("0.3.0-rc.2")
    assert (
        candidate.python_version,
        candidate.npm_version,
        candidate.npm_tag,
        candidate.prerelease,
    ) == ("0.3.0rc2", "0.3.0-rc.2", "next", True)


def test_github_state_machine_covers_missing_exact_conflict_and_unexpected(
    tmp_path: Path,
) -> None:
    directory, _ = _candidate(tmp_path)
    write_controls(directory)
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    expected = expected_github_assets(directory, manifest)

    missing = classify_github(manifest, expected, None)
    assert missing.state == "missing"
    assert missing.release == "absent"
    assert missing.missing == tuple(sorted(expected))

    payload = _github_payload(directory)
    exact = classify_github(manifest, expected, payload)
    assert exact.state == "exact"
    assert exact.release == "draft"

    published = _github_payload(directory, draft=False)
    exact_published = classify_github(manifest, expected, published)
    assert exact_published.state == "exact"
    assert exact_published.release == "published"

    mutable_published = _github_payload(directory, draft=False)
    mutable_published["immutable"] = False
    mutable_conflict = classify_github(manifest, expected, mutable_published)
    assert mutable_conflict.state == "conflict"
    assert "published_release_not_immutable" in {
        problem.code for problem in mutable_conflict.problems
    }

    published["assets"].pop()
    immutable_conflict = classify_github(manifest, expected, published)
    assert immutable_conflict.state == "conflict"
    assert "published_release_missing_assets" in {
        problem.code for problem in immutable_conflict.problems
    }

    partial = _github_payload(directory)
    removed = partial["assets"].pop()["name"]
    decision = classify_github(manifest, expected, partial)
    assert decision.state == "missing"
    assert decision.missing == (removed,)

    mismatch = _github_payload(directory)
    mismatch["assets"][0]["digest"] = "sha256:" + "0" * 64
    decision = classify_github(manifest, expected, mismatch)
    assert decision.state == "conflict"
    assert "digest_mismatch" in {problem.code for problem in decision.problems}

    unexpected = _github_payload(directory)
    unexpected["assets"].append(
        {
            "name": "unknown.bin",
            "state": "uploaded",
            "size": 1,
            "digest": "sha256:" + "0" * 64,
        }
    )
    decision = classify_github(manifest, expected, unexpected)
    assert decision.state == "unexpected"
    assert "unexpected_asset" in {problem.code for problem in decision.problems}

    duplicate = _github_payload(directory)
    duplicate["assets"].append(dict(duplicate["assets"][0]))
    forward = classify_github(manifest, expected, duplicate).to_dict()
    duplicate["assets"].reverse()
    assert classify_github(manifest, expected, duplicate).to_dict() == forward
    assert "duplicate_asset" in {problem["code"] for problem in forward["problems"]}


def test_github_uses_fallback_digest_and_enforces_prerelease_flag(tmp_path: Path) -> None:
    directory, _ = _candidate(tmp_path, "0.3.0-rc.2")
    write_controls(directory)
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    expected = expected_github_assets(directory, manifest)
    payload = _github_payload(directory)
    first = payload["assets"][0]
    first["digest"] = None
    fallback = {first["name"]: expected[first["name"]].sha256}
    assert classify_github(manifest, expected, payload, fallback).state == "exact"

    payload["prerelease"] = False
    decision = classify_github(manifest, expected, payload, fallback)
    assert decision.state == "conflict"
    assert "prerelease_mismatch" in {problem.code for problem in decision.problems}


def test_github_latest_classification_preserves_stable_and_prerelease_channels(
    tmp_path: Path,
) -> None:
    stable_directory, _ = _candidate(tmp_path / "stable")
    stable = load_manifest(stable_directory / RELEASE_MANIFEST_NAME)
    assert classify_github_latest(stable, {"tag_name": "v0.3.0"}) == ()
    assert {problem.code for problem in classify_github_latest(stable, None)} == {
        "latest_release_absent"
    }
    assert {problem.code for problem in classify_github_latest(stable, {"tag_name": "v0.2.2"})} == {
        "latest_tag_mismatch"
    }

    rc_directory, _ = _candidate(tmp_path / "rc", "0.3.0-rc.2")
    candidate = load_manifest(rc_directory / RELEASE_MANIFEST_NAME)
    assert classify_github_latest(candidate, None) == ()
    assert classify_github_latest(candidate, {"tag_name": "v0.2.2"}) == ()
    assert {
        problem.code for problem in classify_github_latest(candidate, {"tag_name": "v0.3.0-rc.2"})
    } == {"prerelease_is_latest"}


def test_github_fallback_downloads_only_exactly_sized_expected_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory, _ = _candidate(tmp_path / "candidate")
    write_controls(directory)
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    expected = expected_github_assets(directory, manifest)
    target_name = manifest.one("npm").name
    payload = _github_payload(directory)
    target = next(item for item in payload["assets"] if item["name"] == target_name)
    target["digest"] = None
    payload["assets"].append(
        {
            "name": "unexpected.bin",
            "state": "uploaded",
            "size": 1,
            "digest": None,
            "id": 999,
            "url": "https://api.github.com/repos/jlevy/softschema/releases/assets/999",
        }
    )
    fixture = tmp_path / "github.json"
    fixture.write_bytes(_canonical_json(payload))
    downloads: list[tuple[str, int]] = []

    def download(url: str, **kwargs: Any) -> bytes:
        downloads.append((url, kwargs["limit"]))
        return (directory / target_name).read_bytes()

    monkeypatch.setattr(release_state, "_download", download)
    _, fallback = release_state._github_payloads(
        manifest,
        expected,
        "jlevy/softschema",
        f"v{manifest.logical_version}",
        fixture,
        None,
        None,
    )
    assert fallback == {target_name: expected[target_name].sha256}
    assert downloads == [(target["url"], expected[target_name].size)]

    target["size"] = expected[target_name].size + 1
    fixture.write_bytes(_canonical_json(payload))
    downloads.clear()
    _, fallback = release_state._github_payloads(
        manifest,
        expected,
        "jlevy/softschema",
        f"v{manifest.logical_version}",
        fixture,
        None,
        None,
    )
    assert fallback == {}
    assert downloads == []


def test_pypi_integrity_metadata_requires_trusted_publisher_and_subject(tmp_path: Path) -> None:
    directory, _ = _candidate(tmp_path)
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    fixtures = _pypi_integrity_payloads(directory)
    check_pypi_integrity_metadata(manifest, fixtures)

    first = next(iter(fixtures.values()))
    first["attestation_bundles"][0]["attestations"][0]["envelope"]["statement"] = base64.b64encode(
        b'{"subject":[]}'
    ).decode()
    with pytest.raises(ReleaseStateError, match="no exact trusted publisher"):
        check_pypi_integrity_metadata(manifest, fixtures)

    wrong_values = {
        "environment": "other",
        "kind": "Other",
        "repository": "attacker/softschema",
        "workflow": "other.yml",
    }
    for field, value in wrong_values.items():
        fixtures = _pypi_integrity_payloads(directory)
        first = next(iter(fixtures.values()))
        first["attestation_bundles"][0]["publisher"][field] = value
        with pytest.raises(ReleaseStateError, match="no exact trusted publisher"):
            check_pypi_integrity_metadata(manifest, fixtures)


def test_npm_audit_report_requires_exact_verified_attestation_and_source_identity(
    tmp_path: Path,
) -> None:
    directory, values = _candidate(tmp_path)
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    subject = manifest.one("npm")
    npm_bytes = values[subject.name]
    check_npm_audit_attestations(
        directory,
        manifest,
        _npm_audit_report(directory, npm_bytes),
    )

    wrong_version = _npm_audit_report(directory, npm_bytes)
    wrong_version["verified"][0]["version"] = "9.9.9"
    with pytest.raises(ReleaseStateError, match="exactly one verified"):
        check_npm_audit_attestations(directory, manifest, wrong_version)

    no_bundle = _npm_audit_report(directory, npm_bytes)
    no_bundle["verified"][0]["attestationBundles"] = []
    with pytest.raises(ReleaseStateError, match="no attestations"):
        check_npm_audit_attestations(directory, manifest, no_bundle)

    wrong_source = _npm_audit_report(
        directory,
        npm_bytes,
        repository="https://github.com/attacker/softschema",
    )
    with pytest.raises(ReleaseStateError, match="exact trusted source identity"):
        check_npm_audit_attestations(directory, manifest, wrong_source)

    wrong_digest = _npm_audit_report(directory, b"different npm bytes")
    with pytest.raises(ReleaseStateError, match="exact trusted source identity"):
        check_npm_audit_attestations(directory, manifest, wrong_digest)

    wrong_certificate = _npm_audit_report(
        directory,
        npm_bytes,
        certificate_identity="https://github.com/attacker/workflow@refs/tags/v0.3.0",
    )
    with pytest.raises(ReleaseStateError, match="exact trusted source identity"):
        check_npm_audit_attestations(directory, manifest, wrong_certificate)

    expected_identity = (
        f"{NPM_SOURCE_REPOSITORY}/{NPM_SOURCE_WORKFLOW}@refs/tags/v{manifest.logical_version}"
    )
    for ambiguous_identity in (
        f"prefix-{expected_identity}",
        f"{expected_identity}-attacker",
    ):
        report = _npm_audit_report(
            directory,
            npm_bytes,
            certificate_identity=ambiguous_identity,
        )
        with pytest.raises(ReleaseStateError, match="exact trusted source identity"):
            check_npm_audit_attestations(directory, manifest, report)

    invalid = _npm_audit_report(directory, npm_bytes)
    invalid["invalid"] = [{"name": "dependency", "version": "1.0.0"}]
    with pytest.raises(ReleaseStateError, match="invalid or missing"):
        check_npm_audit_attestations(directory, manifest, invalid)


def test_npm_signature_consumer_reuses_frozen_lock_without_resolution(tmp_path: Path) -> None:
    directory, values = _candidate(tmp_path / "candidate")
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    subject = manifest.one("npm")
    bundle = directory / "npm-consumer"
    bundle.mkdir()
    local_spec = f"file:../{subject.name}"
    package = {
        "name": "softschema-artifact-consumer",
        "version": "0.0.0",
        "private": True,
        "dependencies": {"softschema": local_spec},
    }
    lock = {
        "name": package["name"],
        "version": package["version"],
        "lockfileVersion": 3,
        "requires": True,
        "packages": {
            "": {
                "name": package["name"],
                "version": package["version"],
                "dependencies": {"softschema": local_spec},
            },
            "node_modules/softschema": {
                "version": manifest.coordinates.npm_version,
                "resolved": local_spec,
                "integrity": _sha512_integrity(values[subject.name]),
            },
        },
    }
    (bundle / "package.json").write_bytes(_canonical_json(package))
    (bundle / "package-lock.json").write_bytes(_canonical_json(lock))
    output = tmp_path / "audit"

    stage_npm_signature_consumer(directory, output)

    actual_package = json.loads((output / "package.json").read_text(encoding="utf-8"))
    actual_lock = json.loads((output / "package-lock.json").read_text(encoding="utf-8"))
    assert actual_package["dependencies"] == {"softschema": manifest.coordinates.npm_version}
    assert actual_lock["packages"]["node_modules/softschema"]["resolved"] == (
        f"https://registry.npmjs.org/softschema/-/{subject.name}"
    )
    assert actual_lock["packages"]["node_modules/softschema"]["integrity"] == (
        _sha512_integrity(values[subject.name])
    )


def test_plan_commands_use_injected_fixtures_without_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    directory, values = _candidate(tmp_path / "candidate")
    write_controls(directory)
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    package_names = sorted(item.name for item in manifest.by_kind("wheel", "sdist"))
    pypi_fixture = tmp_path / "pypi.json"
    pypi_fixture.write_bytes(_canonical_json(_pypi_payload(directory, package_names)))
    npm_fixture = tmp_path / "npm.json"
    npm_subject = manifest.one("npm")
    npm_fixture.write_bytes(_canonical_json(_npm_payload(directory, values[npm_subject.name])))
    npm_audit_fixture = tmp_path / "npm-audit.json"
    npm_audit_fixture.write_bytes(
        _canonical_json(_npm_audit_report(directory, values[npm_subject.name]))
    )
    github_fixture = tmp_path / "github.json"
    github_fixture.write_bytes(_canonical_json(_github_payload(directory)))

    def unexpected_network(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("fixture-backed plan attempted network access")

    monkeypatch.setattr(release_state, "_download", unexpected_network)
    monkeypatch.setattr(release_state, "_download_json", unexpected_network)

    assert release_state.main(["pypi-plan", str(directory), "--fixture", str(pypi_fixture)]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "complete"
    assert release_state.main(["check-npm-audit", str(directory), str(npm_audit_fixture)]) == 0
    assert (
        release_state.main(
            [
                "npm-plan",
                str(directory),
                "--fixture",
                str(npm_fixture),
                "--tarball-fixture",
                str(directory / npm_subject.name),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["state"] == "complete"
    assert (
        release_state.main(
            [
                "github-plan",
                str(directory),
                "--repo",
                "jlevy/softschema",
                "--tag",
                "v0.3.0",
                "--fixture",
                str(github_fixture),
                "--require-state",
                "exact",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["state"] == "exact"

    github_fixture.write_bytes(_canonical_json(_github_payload(directory, draft=False)))
    latest_fixture = tmp_path / "latest.json"
    latest_fixture.write_bytes(_canonical_json({"tag_name": "v0.3.0"}))
    assert (
        release_state.main(
            [
                "github-plan",
                str(directory),
                "--repo",
                "jlevy/softschema",
                "--tag",
                "v0.3.0",
                "--fixture",
                str(github_fixture),
                "--latest-fixture",
                str(latest_fixture),
                "--require-state",
                "exact",
                "--require-published",
                "--require-latest",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["release"] == "published"

    latest_fixture.write_bytes(_canonical_json({"tag_name": "v0.2.2"}))
    assert (
        release_state.main(
            [
                "github-plan",
                str(directory),
                "--repo",
                "jlevy/softschema",
                "--tag",
                "v0.3.0",
                "--fixture",
                str(github_fixture),
                "--latest-fixture",
                str(latest_fixture),
                "--require-state",
                "exact",
                "--require-published",
                "--require-latest",
            ]
        )
        == 2
    )
    assert "latest_tag_mismatch" in capsys.readouterr().err


def test_npm_plan_does_not_fetch_an_unexpected_registry_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    directory, values = _candidate(tmp_path / "candidate")
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    subject = manifest.one("npm")
    fixture = tmp_path / "npm.json"
    payload = _npm_payload(directory, values[subject.name])
    payload["dist"]["tarball"] = "https://registry.npmjs.org/other/-/other.tgz"
    fixture.write_bytes(_canonical_json(payload))

    def unexpected_network(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("unexpected npm path was fetched")

    monkeypatch.setattr(release_state, "_download", unexpected_network)
    assert release_state.main(["npm-plan", str(directory), "--fixture", str(fixture)]) == 1
    decision = json.loads(capsys.readouterr().out)
    assert decision["state"] == "conflict"
    assert "tarball_url_mismatch" in {problem["code"] for problem in decision["problems"]}


def test_fixture_responses_are_bounded_before_json_parsing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    directory, _ = _candidate(tmp_path / "candidate")
    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * (release_state.MAX_JSON_BYTES + 1))

    assert release_state.main(["pypi-plan", str(directory), "--fixture", str(oversized)]) == 2
    assert f"exceeds the {release_state.MAX_JSON_BYTES}-byte limit" in capsys.readouterr().err


def test_state_driver_runs_from_the_frozen_transfer_with_stdlib_only(tmp_path: Path) -> None:
    directory, _ = _candidate(tmp_path / "candidate")
    driver = directory / "devtools" / "release_state.py"
    driver.parent.mkdir()
    shutil.copy2(ROOT / "devtools/release_state.py", driver)

    process = subprocess.run(
        [sys.executable, "-I", "-S", str(driver), "controls", str(directory)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)[RELEASE_INDEX_NAME] == _sha256(
        (directory / RELEASE_INDEX_NAME).read_bytes()
    )


def test_expired_actions_transfer_recovers_exact_frozen_bytes_with_stdlib_only(
    tmp_path: Path,
) -> None:
    directory, _ = _candidate(tmp_path / "candidate")
    write_controls(directory)
    driver = directory / "devtools" / "release_state.py"
    driver.parent.mkdir()
    shutil.copy2(ROOT / "devtools/release_state.py", driver)
    nested = directory / "npm-consumer" / "package-lock.json"
    nested.parent.mkdir()
    nested.write_bytes(b'{"lockfileVersion":3}\n')
    files = {
        path.relative_to(directory).as_posix(): path
        for path in directory.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    }
    checksums = "".join(f"{_sha256(files[name].read_bytes())}  {name}\n" for name in sorted(files))
    (directory / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    expected = {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }

    first = tmp_path / "release-recovery.tar"
    second = tmp_path / "release-recovery-second.tar"
    first_result = write_recovery_bundle(directory, first)
    write_recovery_bundle(directory, second)
    assert first.read_bytes() == second.read_bytes()
    assert first_result["sha256"] == _sha256(first.read_bytes())

    bootstrap = tmp_path / "release-recovery.py"
    shutil.copy2(driver, bootstrap)
    shutil.rmtree(directory)
    recovered = tmp_path / "recovered"
    process = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(bootstrap),
            "extract-recovery",
            str(first),
            str(recovered),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["sha256"] == first_result["sha256"]
    assert {
        path.relative_to(recovered).as_posix(): path.read_bytes()
        for path in recovered.rglob("*")
        if path.is_file()
    } == expected
    extract_recovery_bundle(first, tmp_path / "recovered-by-library")


def test_recovery_extraction_rejects_overdepth_members_before_parent_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path / "deep.tar"
    name = "/".join(
        [*(f"level-{index}" for index in range(release_state.MAX_RECOVERY_DEPTH + 1)), "file"]
    )
    _write_recovery_archive(bundle, {name: b"payload"})
    staging = tmp_path / ".output.recovery.tmp"
    created: list[Path] = []
    real_mkdir = Path.mkdir

    def track_mkdir(path: Path, *args: Any, **kwargs: Any) -> None:
        created.append(path)
        real_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", track_mkdir)
    with pytest.raises(ReleaseStateError, match="depth limit"):
        extract_recovery_bundle(bundle, tmp_path / "output")
    assert created == [staging]


def test_recovery_extraction_budgets_unique_implied_directories_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path / "sparse-parents.tar"
    _write_recovery_archive(bundle, {"first/a": b"a", "second/b": b"b"})
    monkeypatch.setattr(release_state, "MAX_RECOVERY_NODES", 3)
    staging = tmp_path / ".output.recovery.tmp"
    created: list[Path] = []
    real_mkdir = Path.mkdir

    def track_mkdir(path: Path, *args: Any, **kwargs: Any) -> None:
        created.append(path)
        real_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", track_mkdir)
    with pytest.raises(ReleaseStateError, match="node limit"):
        extract_recovery_bundle(bundle, tmp_path / "output")
    assert created == [staging]


def test_required_registry_state_uses_bounded_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    directory, _ = _candidate(tmp_path)
    manifest = load_manifest(directory / RELEASE_MANIFEST_NAME)
    names = sorted(subject.name for subject in manifest.by_kind("wheel", "sdist"))
    responses = [None, _pypi_payload(directory, names[:1]), _pypi_payload(directory, names)]

    monkeypatch.setattr(release_state, "_pypi_payload", lambda *args: responses.pop(0))
    assert (
        release_state.main(
            [
                "pypi-plan",
                str(directory),
                "--require-state",
                "complete",
                "--attempts",
                "3",
                "--delay",
                "0",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["state"] == "complete"
    assert responses == []

    assert (
        release_state.main(
            [
                "pypi-plan",
                str(directory),
                "--require-state",
                "complete",
                "--attempts",
                "21",
            ]
        )
        == 2
    )
    assert "attempts must be between" in capsys.readouterr().err


def test_retry_never_retains_complete_decision_when_every_postcondition_fails() -> None:
    postcondition_calls = 0

    def fail_postcondition() -> None:
        nonlocal postcondition_calls
        postcondition_calls += 1
        raise release_state.NetworkStateError("publisher metadata has not propagated")

    with pytest.raises(release_state.NetworkStateError, match="has not propagated"):
        release_state._retry(
            lambda: release_state.Decision("complete"),
            required_state="complete",
            attempts=3,
            delay=0,
            after_complete=fail_postcondition,
        )
    assert postcondition_calls == 3


@pytest.mark.parametrize("delay", [float("nan"), float("inf"), float("-inf"), -0.1])
def test_retry_rejects_nonfinite_or_negative_delays_before_operation(delay: float) -> None:
    called = False

    def operation() -> release_state.Decision:
        nonlocal called
        called = True
        return release_state.Decision("complete")

    with pytest.raises(ReleaseStateError, match="finite and between"):
        release_state._retry(
            operation,
            required_state="complete",
            attempts=1,
            delay=delay,
        )
    assert not called


def test_publish_workflow_has_manifest_driven_release_dag_and_least_privilege() -> None:
    yaml = YAML(typ="safe")
    yaml.allow_duplicate_keys = False
    workflow = yaml.load(ROOT / ".github/workflows/publish.yml")
    jobs = workflow["jobs"]

    def assert_trusted_checkout(job: dict[str, Any]) -> None:
        steps = job["steps"]
        assert isinstance(steps, list)
        checkouts = [
            step
            for step in steps
            if isinstance(step, dict) and str(step.get("uses", "")).startswith("actions/checkout@")
        ]
        assert len(checkouts) == 1
        assert checkouts[0]["with"] == {
            "fetch-depth": 1,
            "persist-credentials": False,
            "ref": "${{ needs.preflight.outputs.source-commit }}",
        }

    assert workflow["permissions"] == {}
    assert jobs["preflight"]["permissions"] == {"contents": "read"}
    assert jobs["draft-release"]["permissions"] == {
        "attestations": "write",
        "contents": "write",
        "id-token": "write",
    }
    attest = next(
        step
        for step in jobs["draft-release"]["steps"]
        if step.get("with", {}).get("subject-checksums") == f"release-out/{PRIMARY_CHECKSUMS_NAME}"
    )
    assert attest["uses"] == "actions/attest@a1948c3f048ba23858d222213b7c278aabede763"
    assert attest["with"]["subject-checksums"] == f"release-out/{PRIMARY_CHECKSUMS_NAME}"
    assert "push-to-registry" not in attest["with"]
    assert "artifact-metadata" not in jobs["draft-release"]["permissions"]
    recovery_attest = next(
        step
        for step in jobs["draft-release"]["steps"]
        if step.get("with", {}).get("subject-checksums") == "recovery/release-recovery.sha256"
    )
    assert recovery_attest["uses"] == ("actions/attest@a1948c3f048ba23858d222213b7c278aabede763")
    recovery_checksum_attest = next(
        step
        for step in jobs["draft-release"]["steps"]
        if step.get("with", {}).get("subject-path") == "recovery/release-recovery.sha256"
    )
    assert recovery_checksum_attest["uses"] == (
        "actions/attest@a1948c3f048ba23858d222213b7c278aabede763"
    )
    for name in ["publish-pypi", "publish-npm"]:
        job = jobs[name]
        assert job["permissions"] == {
            "attestations": "read",
            "contents": "read",
            "id-token": "write",
        }
        scripts = "\n".join(step.get("run", "") for step in job["steps"])
        assert not any(
            forbidden in scripts
            for forbidden in [
                "uv sync",
                "uv build",
                "npm install",
                "npm ci",
                "bun install",
                "pytest",
            ]
        )
        assert_trusted_checkout(job)
    for name in ["draft-release", "publish-pypi", "publish-npm", "finalize-release"]:
        job = jobs[name]
        scripts = "\n".join(step.get("run", "") for step in job["steps"])
        assert_trusted_checkout(job)
        assert not any(
            forbidden in scripts
            for forbidden in [
                "uv sync",
                "uv build",
                "npm install",
                "npm ci",
                "bun install",
                "bun run",
                "pytest",
            ]
        )
    assert jobs["finalize-release"]["needs"] == [
        "preflight",
        "draft-release",
        "verify-pypi",
        "verify-npm",
    ]
    assert jobs["finalize-release"]["permissions"] == {
        "attestations": "read",
        "contents": "write",
    }
    for name in [
        "draft-release",
        "classify-registries",
        "publish-pypi",
        "publish-npm",
        "verify-pypi",
        "verify-npm",
        "finalize-release",
    ]:
        assert "github.event_name == 'push'" in jobs[name]["if"]
        candidate = next(
            step
            for step in jobs[name]["steps"]
            if step["name"] == "Download immutable candidate transfer"
        )
        assert candidate["continue-on-error"] is True
        recovery = next(
            step
            for step in jobs[name]["steps"]
            if step["name"] == "Recover the exact transfer from durable draft assets"
        )
        recovery_script = recovery["run"]
        checksum_attestation = recovery_script.index(
            'gh attestation verify "recovery/release-recovery.sha256"'
        )
        checksum_parse = recovery_script.index("sha256sum --check --strict release-recovery.sha256")
        bootstrap = recovery_script.index("python3 recovery/release-recovery.py extract-recovery")
        assert checksum_attestation < checksum_parse < bootstrap
        before_bootstrap = recovery_script[:bootstrap]
        assert before_bootstrap.count('--source-digest "$GITHUB_SHA"') == 2
        assert before_bootstrap.count('--source-ref "$GITHUB_REF"') == 2
        assert "^[0-9a-f]{64}  release-recovery\\.tar$" in before_bootstrap
        assert "^[0-9a-f]{64}  release-recovery\\.py$" in before_bootstrap
        assert "wc -c < recovery/release-recovery.sha256" in before_bootstrap
        assert "! LC_ALL=C grep -Ev" in before_bootstrap
        after_bootstrap = recovery_script[bootstrap:]
        assert '--source-digest "$SOURCE_COMMIT"' in after_bootstrap
        assert "release-recovery.py release-recovery.sha256" in after_bootstrap
    checksum_pattern_match = re.search(
        r"! LC_ALL=C grep -Ev \\\n\s+'([^']+)'",
        recovery_script,
    )
    assert checksum_pattern_match is not None
    checksum_pattern = re.compile(checksum_pattern_match.group(1))
    digest = "0" * 64
    assert checksum_pattern.fullmatch(f"{digest}  release-recovery.tar")
    assert checksum_pattern.fullmatch(f"{digest}  release-recovery.py")
    for unsafe_name in (
        "/dev/zero",
        "/tmp/release-recovery.tar",
        "../release-recovery.tar",
        "nested/../../release-recovery.py",
    ):
        assert checksum_pattern.fullmatch(f"{digest}  {unsafe_name}") is None
    publish_step = next(
        step
        for step in jobs["finalize-release"]["steps"]
        if step["name"] == "Publish only after both registries verify"
    )
    publish_script = publish_step["run"].strip()
    assert publish_script.startswith('test "$(gh api \\')
    assert publish_script.index("repos/$GITHUB_REPOSITORY/immutable-releases") < (
        publish_script.index("gh release edit")
    )
    preflight_steps = [step["name"] for step in jobs["preflight"]["steps"]]
    assert preflight_steps.index(
        "Generate non-cyclic release controls and freeze the state driver"
    ) < (preflight_steps.index("Generate transfer checksums last"))
    workflow_text = (ROOT / ".github/workflows/publish.yml").read_text(encoding="utf-8")
    assert "release_state.py pypi-plan" in workflow_text
    assert "release_state.py npm-plan" in workflow_text
    assert "release_state.py github-plan" in workflow_text
    assert "python -m devtools.release" in workflow_text
    assert "python devtools/release.py" not in workflow_text
    assert "npm audit signatures --json --include-attestations" in workflow_text
    assert "release_state.py check-npm-audit" in workflow_text
    assert "gh attestation verify" in workflow_text
    assert "release_state.py recovery-bundle" in workflow_text
    assert "--require-published --require-latest" in workflow_text
    assert "--recovery-directory recovery" in workflow_text
    assert "repos/$GITHUB_REPOSITORY/immutable-releases" in workflow_text
    assert 'test "$GITHUB_REPOSITORY" = "jlevy/softschema"' in workflow_text
    assert "--require-publisher-metadata" in workflow_text
    assert "--require-provenance" not in workflow_text
    assert "github.event_name == 'push'" in jobs["draft-release"]["if"]
