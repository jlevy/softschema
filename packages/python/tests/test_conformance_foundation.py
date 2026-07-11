"""Draft conformance-kit integrity and runner tests."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict
from referencing import Registry, Resource
from ruamel.yaml import YAML

import conformance.adapters.python_adapter as python_adapter
import conformance.consumer as conformance_consumer
import conformance.publication as publication
from conformance.publication import PublicationError, build_publication_candidate
from conformance.run import (
    ConformanceError,
    _canonical_json,
    _check_compiled_schema_digest,
    _check_vector_case_ids,
    _load_json,
    _parse_json,
    _select_schema,
    build_integrity_lock,
    load_corpus,
)
from devtools.release import build_conformance_archive
from softschema import SoftField, compile_model, validate_schema_id

ROOT = Path(__file__).parents[3]
CONFORMANCE = ROOT / "conformance"
SCHEMAS = CONFORMANCE / "schemas"
MANIFEST = CONFORMANCE / "manifest.yaml"
INVALID_ADAPTER_REQUESTS: list[dict[str, Any]] = json.loads(
    (ROOT / "tests/parity/conformance-adapter-invalid-requests.json").read_text(encoding="utf-8")
)

EXPECTED_SCHEMAS = {
    "artifact-input-result-v1.schema.json",
    "build-metadata.schema.json",
    "case.schema.json",
    "compiler-input-profile.schema.json",
    "compiled-schema-profile.schema.json",
    "doctor-result.schema.json",
    "conformance-evolution.schema.json",
    "implementation-matrix.schema.json",
    "manifest.schema.json",
    "metadata.schema.json",
    "public-claims.schema.json",
    "release-manifest.schema.json",
    "release-metadata.schema.json",
    "structural-error.schema.json",
    "publication-candidate.schema.json",
    "resource-bundle.schema.json",
    "validation-result-diagnostic-v1.schema.json",
    "validation-result-legacy.schema.json",
    "vector-suite.schema.json",
    "x-softschema.schema.json",
}

EXPECTED_COVERAGE_FAMILIES = {
    "artifact_metadata",
    "artifact_profiles",
    "core_api",
    "diagnostic_v1",
    "format_annotations",
    "legacy_result",
    "metadata",
    "nested_identities",
    "offline_resources",
    "portable_regex",
    "portable_values",
    "raw_canonicalization",
    "resource_bundles",
    "schema_errors",
}


def _load_yaml(path: Path) -> Any:
    return YAML(typ="safe").load(path)


def _load_schemas() -> dict[str, dict[str, Any]]:
    return {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(SCHEMAS.glob("*.schema.json"))
    }


def _registry(schemas: dict[str, dict[str, Any]]) -> Registry[Any]:
    registry: Registry[Any] = Registry()
    for schema in schemas.values():
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return registry


def test_draft_schemas_are_complete_and_metaschema_valid() -> None:
    schemas = _load_schemas()
    assert set(schemas) == EXPECTED_SCHEMAS
    assert len({schema["$id"] for schema in schemas.values()}) == len(schemas)

    for schema in schemas.values():
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].startswith("urn:softschema:draft:conformance:")
        Draft202012Validator.check_schema(schema)


def test_manifest_paths_digests_and_case_contracts_are_valid() -> None:
    schemas = _load_schemas()
    registry = _registry(schemas)
    manifest = _load_yaml(MANIFEST)

    manifest_validator = Draft202012Validator(schemas["manifest.schema.json"], registry=registry)
    assert list(manifest_validator.iter_errors(manifest)) == []

    listed_schemas = {entry["path"] for entry in manifest["schemas"]}
    assert listed_schemas == {f"schemas/{name}" for name in EXPECTED_SCHEMAS}
    assert manifest["cases"]

    case_validator = Draft202012Validator(schemas["case.schema.json"], registry=registry)
    for entry in [*manifest["schemas"], *manifest["cases"]]:
        path = CONFORMANCE / entry["path"]
        assert path.is_file(), entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]

    for entry in manifest["cases"]:
        case_path = CONFORMANCE / entry["path"]
        case = _load_yaml(case_path)
        assert list(case_validator.iter_errors(case)) == []
        assert list(case_validator.iter_errors({**case, "operation": "doctor"}))
        case_dir = case_path.parent
        for file_ref in [
            case["inputs"]["artifact"],
            case["inputs"]["schema"],
            case["expected"]["result"],
        ]:
            referenced = case_dir / file_ref["path"]
            assert referenced.is_file(), file_ref["path"]
            assert hashlib.sha256(referenced.read_bytes()).hexdigest() == file_ref["sha256"]

        expected = json.loads((case_dir / case["expected"]["result"]["path"]).read_text())
        expected_schema = _select_schema(schemas, case["expected"]["schema"])
        validator = Draft202012Validator(expected_schema, registry=registry)
        assert list(validator.iter_errors(expected)) == []


def test_support_schemas_reject_ambiguous_matrix_resource_and_vector_shapes() -> None:
    schemas = _load_schemas()
    implementations = json.loads((CONFORMANCE / "implementations.json").read_text(encoding="utf-8"))
    matrix_validator = Draft202012Validator(schemas["implementation-matrix.schema.json"])
    assert matrix_validator.is_valid(implementations)
    duplicate_python = {
        **implementations,
        "implementations": [implementations["implementations"][0]] * 3,
    }
    assert not matrix_validator.is_valid(duplicate_python)
    wrong_runtime = json.loads(json.dumps(implementations))
    wrong_runtime["implementations"][0]["runtime"] = "bun"
    assert not matrix_validator.is_valid(wrong_runtime)
    missing_tested = json.loads(json.dumps(implementations))
    del missing_tested["implementations"][0]["tested"]
    assert not matrix_validator.is_valid(missing_tested)

    bundle_validator = Draft202012Validator(schemas["resource-bundle.schema.json"])
    for invalid_id in (
        "https:// evil",
        "https://user@example.com/schema",
        "https://example.com\\schema",
        "URN:Example:Value",
    ):
        assert not bundle_validator.is_valid({"root": True, "resources": {invalid_id: True}})
    for resource_id in (
        "https://example.com/schema/v1",
        "urn:example:schema:v1",
    ):
        assert validate_schema_id(resource_id) == resource_id
        assert bundle_validator.is_valid({"root": True, "resources": {resource_id: True}})

    suite = json.loads((CONFORMANCE / "vectors/identity-v1.json").read_text(encoding="utf-8"))
    vector_validator = Draft202012Validator(schemas["vector-suite.schema.json"])
    assert vector_validator.is_valid(suite)
    duplicate_cases = {**suite, "cases": [suite["cases"][0], suite["cases"][0]]}
    with pytest.raises(ConformanceError, match="duplicate vector case id"):
        _check_vector_case_ids(duplicate_cases)
    invalid_identity = json.loads(json.dumps(suite))
    del invalid_identity["cases"][0]["input"]["kind"]
    assert not vector_validator.is_valid(invalid_identity)


def test_manifest_schema_requires_canonical_posix_paths() -> None:
    schema = _load_schemas()["manifest.schema.json"]["$defs"]["path"]
    validator = Draft202012Validator(schema)
    assert validator.is_valid("schemas/example.schema.json")
    for invalid in ("schemas//x.json", "schemas/./x.json", "schemas/../x.json", "schemas/"):
        assert not validator.is_valid(invalid)


def test_completed_kit_declares_every_settled_family_and_support_artifact() -> None:
    corpus = load_corpus()
    manifest = corpus.manifest

    assert set(manifest["coverage"]) == EXPECTED_COVERAGE_FAMILIES
    assert all(manifest["coverage"].values())
    assert manifest["identifier_status"] == "draft-until-live-verification"
    assert manifest["target_namespace"] == "https://jlevy.github.io/softschema/schema/v1/"
    assert {suite["id"] for suite in manifest["vector_suites"]} == {
        "canonicalization-v1",
        "diagnostic-projection-v1",
        "identity-v1",
        "metadata-v1",
        "portable-pattern-v1",
        "portable-yaml-v1",
        "structural-resources-v1",
    }
    assert {artifact["role"] for artifact in manifest["artifacts"]} >= {
        "evolution",
        "implementation-matrix",
        "publication-candidate",
        "walkthrough",
    }
    assert all(case[1]["execution"]["status"] == "ready" for case in corpus.cases)

    targets = json.loads(
        (CONFORMANCE / "skill-installer/agent-targets-v1.json").read_text(encoding="utf-8")
    )
    assert (
        manifest["agent_install_destinations"]["implicit_project_agents"]
        == targets["implicit_project_agents"]
    )
    assert manifest["agent_install_destinations"]["agents"] == {
        target["selector"]: {
            "project": target["project_root"],
            "personal": target["personal_root"],
        }
        for target in targets["agents"]
    }
    assert set(manifest["agent_install_destinations"]["unsupported_agents"]) == {
        target["selector"] for target in targets["unsupported_agents"]
    }


def test_integrity_lock_covers_the_standalone_archive_without_self_reference() -> None:
    corpus = load_corpus()
    expected = build_integrity_lock(corpus)
    actual = json.loads((CONFORMANCE / "manifest.lock.json").read_text(encoding="utf-8"))

    assert actual == expected
    paths = [entry["path"] for entry in actual["files"]]
    assert paths == sorted(paths)
    assert "conformance/manifest.yaml" in paths
    assert "conformance/manifest.lock.json" not in paths
    assert "conformance/consumer.py" in paths
    assert "conformance/WALKTHROUGH.md" in paths


def test_publication_candidate_is_deterministic_and_does_not_promote_sources(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_index = build_publication_candidate(CONFORMANCE, first)
    second_index = build_publication_candidate(CONFORMANCE, second)

    assert first_index == second_index
    assert {
        path.relative_to(first).as_posix(): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    } == {
        path.relative_to(second).as_posix(): path.read_bytes()
        for path in second.rglob("*")
        if path.is_file()
    }
    assert all(
        schema["$id"].startswith("urn:softschema:draft:conformance:")
        for schema in _load_schemas().values()
    )
    for entry in first_index["schemas"]:
        published = json.loads((first / entry["path"]).read_text(encoding="utf-8"))
        assert published["$id"] == entry["id"]
        assert published["$id"].startswith(
            manifest_target := "https://jlevy.github.io/softschema/schema/v1/"
        )
        assert entry["url"] == f"{manifest_target}{Path(entry['path']).name}"
        assert "urn:softschema:draft:" not in json.dumps(published)

    first_schema = first / first_index["schemas"][0]["path"]
    first_schema.write_bytes(b"tampered\n")
    with pytest.raises(PublicationError, match="refusing to replace"):
        build_publication_candidate(CONFORMANCE, first)


def test_public_v1_schemas_accept_the_intended_released_kit_state(tmp_path: Path) -> None:
    index = build_publication_candidate(CONFORMANCE, tmp_path)
    published = {
        Path(entry["path"]).name: json.loads((tmp_path / entry["path"]).read_text(encoding="utf-8"))
        for entry in index["schemas"]
    }
    assert all(not schema["title"].startswith("Draft ") for schema in published.values())

    released_manifest = _load_yaml(MANIFEST)
    released_manifest["kit_version"] = "1.0.0"
    released_manifest["status"] = "released"
    released_manifest["identifier_status"] = "published"
    released_manifest["vocabulary"]["uri"] = f"{publication.TARGET_NAMESPACE}vocab/x-softschema"
    for entry in released_manifest["schemas"]:
        entry["id"] = f"{publication.TARGET_NAMESPACE}{Path(entry['path']).name}"
    assert Draft202012Validator(published["manifest.schema.json"]).is_valid(released_manifest)

    released_evolution = json.loads((CONFORMANCE / "evolution.json").read_text(encoding="utf-8"))
    released_evolution["current"] = "1.0.0"
    released_evolution["identifier_status"] = "published"
    released_evolution["history"].append(
        {"version": "1.0.0", "status": "released", "compatibility": "initial"}
    )
    assert Draft202012Validator(published["conformance-evolution.schema.json"]).is_valid(
        released_evolution
    )


def test_publication_rewrites_only_identifier_bearing_mapping_keys() -> None:
    schema_id = "urn:softschema:draft:conformance:example:v0"
    schema_url = f"{publication.TARGET_NAMESPACE}example.schema.json"
    vocabulary_url = f"{publication.TARGET_NAMESPACE}vocab/x-softschema"
    replacements = {
        schema_id: schema_url,
        publication.DRAFT_VOCABULARY_URI: vocabulary_url,
        publication.DRAFT_SCHEMA_ID_PATTERN: (
            f"^{re.escape(publication.TARGET_NAMESPACE)}[a-z0-9-]+\\.schema\\.json$"
        ),
    }
    original = {
        "$id": schema_id,
        "$vocabulary": {publication.DRAFT_VOCABULARY_URI: False},
        "properties": {
            schema_id: {
                "$ref": f"{schema_id}#/$defs/value",
                "const": publication.DRAFT_VOCABULARY_URI,
            }
        },
        "required": [schema_id],
        "dependentRequired": {schema_id: [publication.DRAFT_VOCABULARY_URI]},
        "$defs": {
            publication.DRAFT_VOCABULARY_URI: {
                "const": publication.DRAFT_SCHEMA_ID_PATTERN,
                "pattern": publication.DRAFT_SCHEMA_ID_PATTERN,
            }
        },
        "x-extension": {"$vocabulary": {publication.DRAFT_VOCABULARY_URI: False}},
        "x-extension-scalar": schema_id,
        publication.DRAFT_VOCABULARY_URI: {schema_id: "extension-name-is-inert"},
    }

    replaced = publication._replace_identifiers(original, replacements)

    assert replaced["$id"] == schema_url
    assert replaced["$vocabulary"] == {vocabulary_url: False}
    assert schema_id in replaced["properties"]
    assert replaced["properties"][schema_id]["$ref"] == f"{schema_url}#/$defs/value"
    assert replaced["properties"][schema_id]["const"] == vocabulary_url
    assert publication.DRAFT_VOCABULARY_URI in replaced["$defs"]
    assert (
        replaced["$defs"][publication.DRAFT_VOCABULARY_URI]["const"]
        == publication.DRAFT_SCHEMA_ID_PATTERN
    )
    assert (
        replaced["$defs"][publication.DRAFT_VOCABULARY_URI]["pattern"]
        == replacements[publication.DRAFT_SCHEMA_ID_PATTERN]
    )
    assert publication.DRAFT_VOCABULARY_URI in replaced
    assert schema_id in replaced[publication.DRAFT_VOCABULARY_URI]
    assert publication.DRAFT_VOCABULARY_URI in replaced["x-extension"]["$vocabulary"]
    assert replaced["required"] == [schema_id]
    assert replaced["dependentRequired"] == {schema_id: [publication.DRAFT_VOCABULARY_URI]}
    assert replaced["x-extension-scalar"] == schema_id


def test_publication_config_requires_the_exact_settled_v1_policy() -> None:
    valid = json.loads((CONFORMANCE / "publication.json").read_text(encoding="utf-8"))
    publication._validate_publication_config(valid)

    extra = {**valid, "unreviewed": True}
    wrong_type = {**valid, "promotion_gate": {**valid["promotion_gate"], "http_status": True}}
    wrong_target = {**valid, "target_namespace": "https://example.invalid/schema/v1/"}
    for malformed in (extra, wrong_type, wrong_target):
        with pytest.raises(PublicationError, match="publication config"):
            publication._validate_publication_config(malformed)


@pytest.mark.parametrize(
    "content",
    [
        ("[" * 1200 + "]" * 1200).encode(),
        ('{"value":' + "9" * 5000 + "}").encode(),
        b'{"value":1e999}',
        b'{"value":"\\ud800"}',
        b'{"\\udfff":true}',
    ],
)
def test_publication_strict_json_normalizes_bounded_parser_failures(
    tmp_path: Path, content: bytes
) -> None:
    path = tmp_path / "input.json"
    path.write_bytes(content)
    with pytest.raises(PublicationError, match=r"(?:strict JSON|non-finite)"):
        publication._strict_json(
            path,
            root=tmp_path,
            max_bytes=publication.MAX_PUBLICATION_INDEX_BYTES,
            description="test input",
        )


def test_publication_strict_json_rejects_oversize_before_parsing(tmp_path: Path) -> None:
    path = tmp_path / "input.json"
    path.write_bytes(b" " * (publication.MAX_PUBLICATION_CONFIG_BYTES + 1))
    with pytest.raises(PublicationError, match="exceeds the byte limit"):
        publication._strict_json(
            path,
            root=tmp_path,
            max_bytes=publication.MAX_PUBLICATION_CONFIG_BYTES,
            description="test input",
        )


def _write_publication_source(
    root: Path,
    schemas: dict[str, dict[str, Any]],
) -> None:
    root.mkdir()
    (root / "publication.json").write_bytes((CONFORMANCE / "publication.json").read_bytes())
    schema_root = root / "schemas"
    schema_root.mkdir()
    for name, schema in schemas.items():
        (schema_root / name).write_text(json.dumps(schema), encoding="utf-8")


def test_publication_builder_rejects_duplicate_ids_before_writing(tmp_path: Path) -> None:
    source = tmp_path / "source"
    schema_id = "urn:softschema:draft:conformance:duplicate:v0"
    _write_publication_source(
        source,
        {
            "first.schema.json": {"$id": schema_id},
            "second.schema.json": {"$id": schema_id},
        },
    )
    output = tmp_path / "output"
    with pytest.raises(PublicationError, match="duplicate source schema id"):
        build_publication_candidate(source, output)
    assert not output.exists()


def test_publication_builder_rejects_noncanonical_filename_before_writing(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _write_publication_source(
        source,
        {
            "Upper.schema.json": {
                "$id": "urn:softschema:draft:conformance:upper:v0",
            }
        },
    )
    output = tmp_path / "output"
    with pytest.raises(PublicationError, match="filename is noncanonical"):
        build_publication_candidate(source, output)
    assert not output.exists()


def test_publication_builder_rejects_unresolved_draft_reference_before_writing(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _write_publication_source(
        source,
        {
            "example.schema.json": {
                "$id": "urn:softschema:draft:conformance:example:v0",
                "$ref": "urn:softschema:draft:conformance:missing:v0",
            }
        },
    )
    output = tmp_path / "output"
    with pytest.raises(PublicationError, match="unresolved draft identifier"):
        build_publication_candidate(source, output)
    assert not output.exists()


def test_publication_builder_enforces_total_source_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    _write_publication_source(
        source,
        {
            "example.schema.json": {
                "$id": "urn:softschema:draft:conformance:example:v0",
            }
        },
    )
    monkeypatch.setattr(publication, "MAX_PUBLICATION_BUNDLE_BYTES", 1)
    output = tmp_path / "output"
    with pytest.raises(PublicationError, match="source bundle exceeds"):
        build_publication_candidate(source, output)
    assert not output.exists()


def test_publication_builder_rejects_symlinked_output_escape(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _write_publication_source(
        source,
        {
            "example.schema.json": {
                "$id": "urn:softschema:draft:conformance:example:v0",
            }
        },
    )
    output = tmp_path / "output"
    output.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (output / "schema").symlink_to(outside, target_is_directory=True)
    except OSError as exc:  # Windows CI may not grant symlink creation.
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(PublicationError, match="symlink"):
        build_publication_candidate(source, output)
    assert not (outside / "v1").exists()


def test_publication_builder_rejects_broken_output_file_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _write_publication_source(
        source,
        {
            "example.schema.json": {
                "$id": "urn:softschema:draft:conformance:example:v0",
            }
        },
    )
    output = tmp_path / "output"
    target = output / "schema/v1/example.schema.json"
    target.parent.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    try:
        target.symlink_to(outside)
    except OSError as exc:  # Windows CI may not grant symlink creation.
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(PublicationError, match="symlink"):
        build_publication_candidate(source, output)
    assert not outside.exists()


def test_publication_builder_rejects_undeclared_output_before_writing(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _write_publication_source(
        source,
        {
            "example.schema.json": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "urn:softschema:draft:conformance:example:v0",
                "type": "object",
            }
        },
    )
    output = tmp_path / "output"
    output.mkdir()
    (output / "stale.html").write_text("stale", encoding="utf-8")

    with pytest.raises(PublicationError, match="undeclared file"):
        build_publication_candidate(source, output)
    assert not (output / "schema").exists()


def _one_schema_candidate_index(data: bytes) -> dict[str, Any]:
    filename = "example.schema.json"
    url = f"{publication.TARGET_NAMESPACE}{filename}"
    return {
        "format": publication.PUBLICATION_INDEX_FORMAT,
        "source_identifier_status": publication.SOURCE_IDENTIFIER_STATUS,
        "target_namespace": publication.TARGET_NAMESPACE,
        "version": publication.PUBLICATION_VERSION,
        "schemas": [
            {
                "id": url,
                "path": f"schema/v1/{filename}",
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
                "url": url,
            }
        ],
    }


def _write_one_schema_candidate(root: Path, data: bytes = b"{}\n") -> dict[str, Any]:
    index = _one_schema_candidate_index(data)
    schema_path = root / index["schemas"][0]["path"]
    schema_path.parent.mkdir(parents=True)
    schema_path.write_bytes(data)
    index_path = root / "schema/v1/index.json"
    index_bytes = publication._json_bytes(index)
    index_path.write_bytes(index_bytes)
    namespace = publication._build_namespace_index(
        {
            index["schemas"][0]["path"]: data,
            "schema/v1/index.json": index_bytes,
        }
    )
    (root / publication.NAMESPACE_INDEX_PATH).write_bytes(publication._json_bytes(namespace))
    return index


def _published_response(url: str, body: bytes) -> MagicMock:
    response = MagicMock()
    response.status = 200
    response.headers.get_content_type.return_value = "application/schema+json"
    response.url = url
    response.read.side_effect = lambda limit: body[:limit]
    response.__enter__.return_value = response
    return response


def _not_found(url: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, 404, "Not Found", Message(), None)


def test_predeploy_allows_only_wholly_absent_or_exact_live_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = _write_one_schema_candidate(tmp_path)
    namespace_url = publication.NAMESPACE_INDEX_URL
    index_url = f"{publication.TARGET_NAMESPACE}index.json"
    schema_url = index["schemas"][0]["url"]
    opener = MagicMock()
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_args: opener)

    def all_missing(request: Any, **_kwargs: Any) -> MagicMock:
        raise _not_found(request.full_url)

    opener.open.side_effect = all_missing
    assert publication.verify_predeploy_candidate(tmp_path)["state"] == "absent"

    namespace_bytes = (tmp_path / publication.NAMESPACE_INDEX_PATH).read_bytes()
    index_bytes = (tmp_path / "schema/v1/index.json").read_bytes()
    schema_bytes = (tmp_path / index["schemas"][0]["path"]).read_bytes()
    exact_bodies = {
        namespace_url: namespace_bytes,
        index_url: index_bytes,
        schema_url: schema_bytes,
    }
    opener.open.side_effect = lambda request, **_kwargs: _published_response(
        request.full_url,
        exact_bodies[request.full_url],
    )
    assert publication.verify_predeploy_candidate(tmp_path)["state"] == "exact"


def test_predeploy_rejects_absence_after_reviewed_promotion_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate"
    _write_one_schema_candidate(candidate)
    marker = tmp_path / "publication-promoted.sha256"
    marker.write_text(
        hashlib.sha256((candidate / publication.NAMESPACE_INDEX_PATH).read_bytes()).hexdigest()
        + "\n",
        encoding="ascii",
    )
    opener = MagicMock()
    opener.open.side_effect = _not_found(publication.NAMESPACE_INDEX_URL)
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_args: opener)

    with pytest.raises(PublicationError, match="promoted namespace index is unavailable"):
        publication.verify_predeploy_candidate(candidate, promotion_marker=marker)
    assert opener.open.call_count == 1


def test_predeploy_rejects_a_promotion_marker_for_different_namespace_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate"
    _write_one_schema_candidate(candidate)
    marker = tmp_path / "publication-promoted.sha256"
    marker.write_text(f"{'0' * 64}\n", encoding="ascii")
    opener = MagicMock()
    opener.open.return_value = _published_response(
        publication.NAMESPACE_INDEX_URL,
        (candidate / publication.NAMESPACE_INDEX_PATH).read_bytes(),
    )
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_args: opener)

    with pytest.raises(PublicationError, match="live namespace index conflicts"):
        publication.verify_predeploy_candidate(candidate, promotion_marker=marker)
    assert opener.open.call_count == 1


def test_namespace_index_rejects_unsafe_or_ambiguous_entries() -> None:
    valid = publication._build_namespace_index({"schema/v1/index.json": b"{}\n"})
    base = valid["files"][0]
    malformed_entries = (
        {**base, "path": "schema/../secret.json"},
        {**base, "size": True},
        {**base, "sha256": "A" * 64},
        {**base, "content_types": ["text/plain", "application/json"]},
    )
    for entry in malformed_entries:
        with pytest.raises(PublicationError, match=r"namespace index\.files\[0\]"):
            publication._validate_namespace_index({**valid, "files": [entry]})


def test_predeploy_reconstructs_the_complete_append_only_live_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = _write_one_schema_candidate(tmp_path)
    index_bytes = (tmp_path / "schema/v1/index.json").read_bytes()
    schema_path = index["schemas"][0]["path"]
    schema_bytes = (tmp_path / schema_path).read_bytes()
    retained = {
        "index.json": b'{"versions":["v1","v2"]}\n',
        "schema/v2/index.json": b'{"version":"v2"}\n',
    }
    live_files = {
        schema_path: schema_bytes,
        "schema/v1/index.json": index_bytes,
        **retained,
    }
    live_namespace = publication._build_namespace_index(live_files)
    live_bodies = {
        publication.NAMESPACE_INDEX_URL: publication._json_bytes(live_namespace),
        **{f"{publication.PUBLICATION_ROOT}{path}": body for path, body in live_files.items()},
    }
    opener = MagicMock()
    opener.open.side_effect = lambda request, **_kwargs: _published_response(
        request.full_url,
        live_bodies[request.full_url],
    )
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_args: opener)

    result = publication.verify_predeploy_candidate(tmp_path)

    assert result["state"] == "exact"
    assert {path: (tmp_path / path).read_bytes() for path in retained} == retained
    merged = json.loads((tmp_path / publication.NAMESPACE_INDEX_PATH).read_text(encoding="utf-8"))
    assert [entry["path"] for entry in merged["files"]] == sorted(live_files)


def test_predeploy_rejects_conflicting_or_partial_live_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = _write_one_schema_candidate(tmp_path)
    namespace_url = publication.NAMESPACE_INDEX_URL
    index_url = f"{publication.TARGET_NAMESPACE}index.json"
    schema_url = index["schemas"][0]["url"]
    opener = MagicMock()
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_args: opener)

    conflicting_namespace = publication._build_namespace_index(
        {
            "schema/v1/index.json": b"{}\n",
            index["schemas"][0]["path"]: b"{}\n",
        }
    )
    opener.open.side_effect = [
        _published_response(namespace_url, publication._json_bytes(conflicting_namespace)),
        _published_response(index_url, b"{}\n"),
    ]
    with pytest.raises(PublicationError, match="live path conflicts"):
        publication.verify_predeploy_candidate(tmp_path)

    partial_bodies = {schema_url: b"{}\n"}

    def partial_response(request: Any, **_kwargs: Any) -> MagicMock:
        if request.full_url in partial_bodies:
            return _published_response(request.full_url, partial_bodies[request.full_url])
        raise _not_found(request.full_url)

    opener.open.side_effect = partial_response
    with pytest.raises(PublicationError, match="namespace is partial"):
        publication.verify_predeploy_candidate(tmp_path)


def test_live_index_rejects_unsafe_paths_urls_sizes_and_digests() -> None:
    data = b"{}\n"
    valid = _one_schema_candidate_index(data)
    publication._validate_live_index(valid)
    base = valid["schemas"][0]
    malformed_entries = (
        {**base, "path": "schema/v1/../secret.schema.json"},
        {**base, "url": "https://example.invalid/example.schema.json"},
        {**base, "size": True},
        {**base, "sha256": base["sha256"].upper()},
    )
    for entry in malformed_entries:
        with pytest.raises(PublicationError, match=r"candidate index\.schemas\[0\]"):
            publication._validate_live_index({**valid, "schemas": [entry]})


def test_live_candidate_rejects_undeclared_local_files(tmp_path: Path) -> None:
    _write_one_schema_candidate(tmp_path)
    (tmp_path / "schema/v1/stale.schema.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(PublicationError, match="undeclared file"):
        publication._load_candidate_index(tmp_path)


def test_live_verification_bounds_the_response_read_and_rejects_oversize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = b"{}\n"
    index = _write_one_schema_candidate(tmp_path, data)
    index_path = tmp_path / "schema/v1/index.json"

    response = _published_response(index["schemas"][0]["url"], b"")
    response.read.side_effect = lambda limit: b"x" * limit
    exact_bodies = {
        publication.NAMESPACE_INDEX_URL: (tmp_path / publication.NAMESPACE_INDEX_PATH).read_bytes(),
        f"{publication.TARGET_NAMESPACE}index.json": index_path.read_bytes(),
    }
    opener = MagicMock()

    def oversized_schema(request: Any, **_kwargs: Any) -> MagicMock:
        if request.full_url == index["schemas"][0]["url"]:
            return response
        return _published_response(request.full_url, exact_bodies[request.full_url])

    opener.open.side_effect = oversized_schema
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_args: opener)

    with pytest.raises(PublicationError, match="live body exceeds the byte limit"):
        publication.verify_live_candidate(tmp_path)
    response.read.assert_called_once_with(len(data) + 1)


def test_live_verification_requires_the_exact_published_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_one_schema_candidate(tmp_path)
    opener = MagicMock()
    opener.open.return_value = _published_response(publication.NAMESPACE_INDEX_URL, b"{}\n")
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_args: opener)

    with pytest.raises(PublicationError, match="namespace index differs"):
        publication.verify_live_candidate(tmp_path)
    assert opener.open.call_count == 1


def test_deterministic_archive_has_external_digest_and_kit_only_consumer(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "conformance-kit.tar.gz"
    digest = tmp_path / "conformance-kit.tar.gz.sha256"
    returned = build_conformance_archive(ROOT, archive, digest_output=digest)
    assert digest.read_text(encoding="utf-8") == f"{returned}  {archive.name}\n"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == returned

    extracted = tmp_path / "extracted"
    extracted.mkdir()
    with tarfile.open(archive, "r:gz") as bundle:
        bundle.extractall(extracted, filter="data")
        names = bundle.getnames()
    assert names == sorted(names)
    assert "conformance/manifest.lock.json" in names
    assert "conformance/vectors/portable-yaml-v1.json" in names
    assert "conformance/adapters/javascript-adapter.mjs" in names

    consumer = extracted / "conformance/consumer.py"
    source = consumer.read_text(encoding="utf-8")
    assert "import softschema" not in source
    assert "from softschema" not in source
    assert "ruamel" not in source
    verified = subprocess.run(
        [sys.executable, "-I", str(consumer), "--root", str(extracted), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["ok"] is True

    target = extracted / "conformance/vectors/identity-v1.json"
    target.write_bytes(target.read_bytes() + b"\n")
    tampered = subprocess.run(
        [sys.executable, "-I", str(consumer), "--root", str(extracted), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert tampered.returncode == 1
    assert "size mismatch" in tampered.stderr


def _write_consumer_fixture(
    root: Path,
    *,
    data: bytes = b"portable\n",
    entry_overrides: dict[str, Any] | None = None,
) -> Path:
    conformance = root / "conformance"
    conformance.mkdir()
    target = conformance / "payload.json"
    target.write_bytes(data)
    entry = {
        "path": "conformance/payload.json",
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        **(entry_overrides or {}),
    }
    lock = {
        "files": [entry],
        "format": conformance_consumer.LOCK_FORMAT,
        "kit_version": "0.0.0-draft.1",
    }
    (conformance / "manifest.lock.json").write_text(json.dumps(lock), encoding="utf-8")
    return target


@pytest.mark.parametrize(
    "path",
    [
        "conformance/../outside.json",
        "conformance/./payload.json",
        "conformance//payload.json",
        "conformance\\payload.json",
        "/conformance/payload.json",
        "other/payload.json",
    ],
)
def test_standalone_consumer_rejects_noncanonical_or_traversing_paths(
    tmp_path: Path, path: str
) -> None:
    _write_consumer_fixture(tmp_path, entry_overrides={"path": path})
    with pytest.raises(conformance_consumer.ConsumerError, match="unsafe integrity path"):
        conformance_consumer.verify(tmp_path)


def test_standalone_consumer_rejects_size_mismatch_before_hashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_consumer_fixture(
        tmp_path,
        data=b"x" * (conformance_consumer.HASH_CHUNK_BYTES + 1),
        entry_overrides={"size": 1},
    )
    monkeypatch.setattr(
        conformance_consumer,
        "_hash_file",
        lambda *_args: pytest.fail("size mismatch must be rejected before file hashing"),
    )
    with pytest.raises(conformance_consumer.ConsumerError, match="size mismatch"):
        conformance_consumer.verify(tmp_path)


def test_standalone_consumer_rejects_declared_byte_limits_before_hashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_consumer_fixture(tmp_path, entry_overrides={"size": 2})
    monkeypatch.setattr(conformance_consumer, "MAX_INTEGRITY_FILE_BYTES", 1)
    monkeypatch.setattr(
        conformance_consumer,
        "_hash_file",
        lambda *_args: pytest.fail("declared limits must be rejected before hashing"),
    )
    with pytest.raises(conformance_consumer.ConsumerError, match="file exceeds"):
        conformance_consumer.verify(tmp_path)

    monkeypatch.setattr(conformance_consumer, "MAX_INTEGRITY_FILE_BYTES", 2)
    monkeypatch.setattr(conformance_consumer, "MAX_INTEGRITY_BUNDLE_BYTES", 1)
    with pytest.raises(conformance_consumer.ConsumerError, match="aggregate byte limit"):
        conformance_consumer.verify(tmp_path)


@pytest.mark.parametrize(
    ("entry_overrides", "message"),
    [
        ({"size": True}, "invalid integrity size"),
        ({"sha256": "A" * 64}, "invalid integrity digest"),
    ],
)
def test_standalone_consumer_rejects_non_strict_lock_fields(
    tmp_path: Path, entry_overrides: dict[str, Any], message: str
) -> None:
    _write_consumer_fixture(tmp_path, entry_overrides=entry_overrides)
    with pytest.raises(conformance_consumer.ConsumerError, match=message):
        conformance_consumer.verify(tmp_path)


def test_standalone_consumer_rejects_undeclared_bytecode(tmp_path: Path) -> None:
    _write_consumer_fixture(tmp_path)
    cache = tmp_path / "conformance/__pycache__"
    cache.mkdir()
    (cache / "shadow.cpython-314.pyc").write_bytes(b"untrusted bytecode")
    with pytest.raises(conformance_consumer.ConsumerError, match="undeclared kit files"):
        conformance_consumer.verify(tmp_path)


@pytest.mark.parametrize("relative", ["conformance/empty", "unexpected", "unexpected.txt"])
def test_standalone_consumer_rejects_every_undeclared_archive_node(
    tmp_path: Path, relative: str
) -> None:
    _write_consumer_fixture(tmp_path)
    path = tmp_path / relative
    if path.suffix:
        path.write_text("undeclared\n", encoding="utf-8")
    else:
        path.mkdir()
    with pytest.raises(conformance_consumer.ConsumerError, match="undeclared kit files"):
        conformance_consumer.verify(tmp_path)


def test_standalone_consumer_bounds_archive_inventory(tmp_path: Path, monkeypatch: Any) -> None:
    _write_consumer_fixture(tmp_path)
    original_scandir = os.scandir
    conformance = (tmp_path / "conformance").resolve()
    reads = 0

    class GuardedScandir:
        def __init__(self, path: Any) -> None:
            self._target = Path(path).resolve() == conformance
            self._context = original_scandir(path)
            self._iterator: Any = None

        def __enter__(self) -> GuardedScandir:
            self._iterator = self._context.__enter__()
            return self

        def __exit__(self, *args: Any) -> Any:
            return self._context.__exit__(*args)

        def __iter__(self) -> GuardedScandir:
            return self

        def __next__(self) -> Any:
            nonlocal reads
            if self._target:
                reads += 1
                if reads > 1:
                    pytest.fail("inventory traversal read beyond the remaining node budget")
            return next(self._iterator)

    monkeypatch.setattr(os, "scandir", GuardedScandir)
    monkeypatch.setattr(conformance_consumer, "MAX_INTEGRITY_NODES", 1)
    with pytest.raises(conformance_consumer.ConsumerError, match="node limit"):
        conformance_consumer.verify(tmp_path)
    assert reads == 1


def test_standalone_consumer_rejects_undeclared_symlinks(tmp_path: Path) -> None:
    _write_consumer_fixture(tmp_path)
    link = tmp_path / "conformance/undeclared-link"
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except OSError as exc:  # Windows CI may not grant symlink creation.
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(conformance_consumer.ConsumerError, match="unsafe kit paths"):
        conformance_consumer.verify(tmp_path)


def test_standalone_consumer_rejects_lock_symlink_before_reading(tmp_path: Path) -> None:
    _write_consumer_fixture(tmp_path)
    lock = tmp_path / "conformance/manifest.lock.json"
    lock.unlink()
    outside = tmp_path / "outside.json"
    outside.write_text('{"outside":true}', encoding="utf-8")
    try:
        lock.symlink_to(outside)
    except OSError as exc:  # Windows CI may not grant symlink creation.
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(conformance_consumer.ConsumerError, match="integrity lock"):
        conformance_consumer.verify(tmp_path)


def test_standalone_consumer_rejects_oversize_lock_before_parsing(tmp_path: Path) -> None:
    _write_consumer_fixture(tmp_path)
    lock = tmp_path / "conformance/manifest.lock.json"
    lock.write_bytes(b" " * (conformance_consumer.MAX_INTEGRITY_LOCK_BYTES + 1))
    with pytest.raises(conformance_consumer.ConsumerError, match="exceeds the byte limit"):
        conformance_consumer.verify(tmp_path)


@pytest.mark.parametrize(
    "content",
    [
        "[" * 1200 + "]" * 1200,
        '{"value":' + "9" * 5000 + "}",
        '{"value":1e999}',
        '{"value":"\\ud800"}',
        '{"\\udfff":true}',
    ],
)
def test_standalone_consumer_normalizes_json_parser_failures(tmp_path: Path, content: str) -> None:
    _write_consumer_fixture(tmp_path)
    lock = tmp_path / "conformance/manifest.lock.json"
    lock.write_text(content, encoding="utf-8")
    with pytest.raises(
        conformance_consumer.ConsumerError,
        match=r"(?:integrity lock|non-finite)",
    ):
        conformance_consumer.verify(tmp_path)


def test_vendored_sarif_assets_match_the_projection_fixtures_byte_for_byte() -> None:
    fixture_root = ROOT / "tests/diagnostics/fixtures"
    for name in (
        "sarif-schema-2.1.0-errata01.json",
        "SARIF-SCHEMA-NOTICE.md",
    ):
        assert (CONFORMANCE / "vendor" / name).read_bytes() == (fixture_root / name).read_bytes()


def test_pages_workflow_is_manual_least_privilege_and_verifies_live_bytes() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/conformance-pages.yml")
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {}
    assert workflow["concurrency"]["cancel-in-progress"] is False

    for job in workflow["jobs"].values():
        for step in job["steps"]:
            action = step.get("uses")
            if action is not None:
                assert re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action), action
    assert workflow["jobs"]["build"]["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["deploy"]["permissions"] == {
        "pages": "write",
        "id-token": "write",
    }
    assert workflow["jobs"]["verify"]["permissions"] == {"actions": "read"}
    scripts = "\n".join(
        step.get("run", "") for job in workflow["jobs"].values() for step in job["steps"]
    )
    source_guard = workflow["jobs"]["build"]["steps"][0]
    assert source_guard["env"] == {
        "SOURCE_REPOSITORY": "${{ github.repository }}",
        "SOURCE_REF": "${{ github.ref }}",
        "SOURCE_REF_PROTECTED": "${{ github.ref_protected }}",
    }
    assert '"jlevy/softschema"' in source_guard["run"]
    assert '"refs/heads/main"' in source_guard["run"]
    assert '"true"' in source_guard["run"]
    assert "publication.py build pages-out" in scripts
    assert "publication.py verify-predeploy pages-out" in scripts
    assert "publication.py verify-live pages-out" in scripts
    assert "publication-promoted.sha256" in scripts
    assert "sha256sum pages-out/publication-index.json" in scripts


def test_python_adapter_uses_a_closed_portable_schema_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        tempfile,
        "NamedTemporaryFile",
        lambda *_args, **_kwargs: pytest.fail("NamedTemporaryFile is not Windows-portable"),
    )
    result = python_adapter._structural_result(
        {"name": "Ada"},
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        },
    )
    assert result["ok"] is True


def test_python_adapter_rejects_non_strict_or_malformed_requests() -> None:
    valid = {
        "format": python_adapter.REQUEST_FORMAT,
        "id": "identity-v1",
        "operation": "identity",
        "cases": [
            {
                "id": "valid",
                "input": {"kind": "contract", "value": "example:Record/v1"},
                "expected": {"ok": True, "value": "example:Record/v1"},
            }
        ],
    }
    assert python_adapter._parse_request(json.dumps(valid).encode("utf-8")) == valid
    malformed = (
        b'{"format":"softschema-vector-suite-v1","format":"duplicate"}',
        b'{"value":NaN}',
        b'{"value":1e999}',
        ("[" * 1200 + "]" * 1200).encode(),
        ('{"value":' + "9" * 5000 + "}").encode(),
        b'{"value":"\\ud800"}',
        b'{"\\udfff":true}',
        json.dumps({**valid, "unexpected": True}).encode(),
        json.dumps({**valid, "operation": []}).encode(),
    )
    for request in malformed:
        with pytest.raises(python_adapter.AdapterRequestError):
            python_adapter._parse_request(request)


def test_python_adapter_rejects_shared_invalid_requests_without_a_traceback() -> None:
    adapter = CONFORMANCE / "adapters/python_adapter.py"
    for vector in INVALID_ADAPTER_REQUESTS:
        process = subprocess.run(
            [sys.executable, str(adapter)],
            input=json.dumps(vector["request"]),
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        assert process.returncode == 2, vector["id"]
        assert process.stdout == "", vector["id"]
        assert process.stderr == f"softschema vector adapter: {vector['message']}\n", vector["id"]


def test_python_adapter_normalizes_json_integer_limit_spelling() -> None:
    request = (
        '{"format":"softschema-vector-suite-v1","id":"limit-integer-spelling",'
        '"operation":"portable-yaml","cases":[{"id":"one-point-zero",'
        '"input":{"text":"null","limits":{"max_depth":1.0}},"expected":{}}]}'
    )
    process = subprocess.run(
        [sys.executable, str(CONFORMANCE / "adapters/python_adapter.py")],
        input=request,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    assert process.returncode == 0
    assert process.stderr == ""
    assert json.loads(process.stdout)["results"] == [
        {"id": "one-point-zero", "actual": {"ok": True, "value": None}}
    ]


def test_artifact_metadata_schemas_negotiate_legacy_and_format_1_exactly() -> None:
    schemas = _load_schemas()
    registry = _registry(schemas)
    validator = Draft202012Validator(schemas["metadata.schema.json"], registry=registry)
    vectors = json.loads((ROOT / "tests/parity/artifact-format.json").read_text())

    for vector in vectors:
        valid = not vector.get("error", False)
        raw = vector["raw"]
        assert validator.is_valid(raw) is valid, vector["id"]


def test_x_softschema_is_an_optional_annotation_vocabulary_with_checked_payloads() -> None:
    schemas = _load_schemas()
    registry = _registry(schemas)
    vocabulary = schemas["x-softschema.schema.json"]
    assert vocabulary["$dynamicAnchor"] == "meta"
    assert vocabulary["$vocabulary"]["urn:softschema:draft:vocabulary:x-softschema:v0"] is False

    profile = Draft202012Validator(
        schemas["compiled-schema-profile.schema.json"], registry=registry
    )
    metadata = {
        "contract": "example.docs:Record/v1",
        "schema_sha256": "0" * 64,
        "softschema_format_version": "0.1.0",
    }
    compiled = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "x-softschema": metadata,
    }
    assert profile.is_valid(compiled)
    assert not profile.is_valid(
        {
            **compiled,
            "x-softschema": {**metadata, "runtime_hook": "execute-me"},
        }
    )

    field_annotation = Draft202012Validator(vocabulary["$defs"]["fieldAnnotation"])
    valid_annotation = {
        "group": "taxonomy",
        "owner": "agent",
        "tier": "constrained",
        "repair": "suggest_alias",
    }
    assert field_annotation.is_valid(valid_annotation)
    for invalid in (
        {"owner": "agent"},
        {**valid_annotation, "owner": "runtime"},
        {**valid_annotation, "tier": "approximate"},
        {**valid_annotation, "repair": "execute"},
    ):
        assert not field_annotation.is_valid(invalid)


def test_official_compiler_output_matches_the_settled_profile(
    tmp_path: Path,
) -> None:
    class OfficialModel(BaseModel):
        label: str = SoftField(
            description="Stable label.",
            group="identity",
            owner="human",
            tier="hard_fact",
            repair="safe_coerce",
        )

    class HostileModel(BaseModel):
        model_config = ConfigDict(
            json_schema_extra={"x-softschema": {"runtime_hook": "execute-me"}}
        )
        label: str

    output = tmp_path / "official.schema.yaml"
    compile_model(OfficialModel, output, contract_id="example.docs:Official/v1")
    compiled = _load_yaml(output)
    schemas = _load_schemas()
    registry = _registry(schemas)
    profile = Draft202012Validator(
        schemas["compiled-schema-profile.schema.json"], registry=registry
    )
    vocabulary = Draft202012Validator(schemas["x-softschema.schema.json"], registry=registry)
    assert profile.is_valid(compiled)
    assert vocabulary.is_valid(compiled)
    with pytest.raises(ValueError, match="reserved x-softschema metadata"):
        compile_model(HostileModel, tmp_path / "hostile.schema.yaml", contract_id="Hostile/v1")


def test_phase_one_error_reasons_have_exact_messages_and_required_fields() -> None:
    schemas = _load_schemas()
    registry = _registry(schemas)
    structural = Draft202012Validator(schemas["structural-error.schema.json"], registry=registry)
    schema_invalid_vectors = [
        ("syntax", "compiled schema is not valid YAML or JSON", {}),
        ("value_domain", "compiled schema contains a non-portable YAML value", {}),
        ("root", "compiled schema root must be a mapping", {}),
        (
            "dialect",
            "compiled schema uses an unsupported JSON Schema dialect",
            {"dialect": "https://example.invalid/draft"},
        ),
        ("metaschema", "compiled schema does not conform to Draft 2020-12", {}),
        (
            "identity",
            "compiled schema resource identity is invalid",
            {"detail": "invalid_root_id"},
        ),
        (
            "profile",
            "compiled schema is outside the softschema profile",
            {"detail": "legacy_contract_id_mismatch"},
        ),
        (
            "pattern",
            "compiled schema contains an unsupported or invalid pattern",
            {"pattern": "["},
        ),
        (
            "reference",
            "compiled schema reference is unavailable offline",
            {"reference": "https://example.invalid/schema"},
        ),
        ("compile", "compiled schema could not be compiled", {}),
    ]
    for reason, message, extra in schema_invalid_vectors:
        record = {
            "kind": "schema_invalid",
            "reason": reason,
            "message": message,
            "schema_path": "",
            **extra,
        }
        assert structural.is_valid(record), reason
        assert not structural.is_valid({**record, "message": "engine-specific prose"}), reason
        assert not structural.is_valid({**record, "line": 1}), reason
        for field in extra:
            without_required = {key: value for key, value in record.items() if key != field}
            assert not structural.is_valid(without_required), f"{reason}/{field}"

    invalid_profile_detail = {
        "kind": "schema_invalid",
        "reason": "profile",
        "message": "compiled schema is outside the softschema profile",
        "schema_path": "",
        "detail": "engine_specific_profile_failure",
    }
    assert not structural.is_valid(invalid_profile_detail)

    artifact_input = Draft202012Validator(
        schemas["artifact-input-result-v1.schema.json"], registry=registry
    )
    artifact_vectors = [
        ("parse_error", "frontmatter", "artifact frontmatter delimiters are malformed", {}),
        ("parse_error", "syntax", "artifact is not valid YAML", {}),
        ("parse_error", "root", "artifact YAML root must be a mapping", {}),
        (
            "parse_error",
            "value_domain",
            "artifact contains a non-portable YAML value",
            {"path": "/movie/year"},
        ),
        ("input_error", "not_found", "artifact path does not exist", {}),
        ("input_error", "unreadable", "artifact path cannot be read", {}),
        (
            "input_error",
            "directory_requires_recursive",
            "artifact directory requires --recursive",
            {},
        ),
        (
            "input_error",
            "no_matches",
            "artifact directory contains no matching files",
            {},
        ),
        (
            "input_error",
            "discovery_limit",
            "artifact discovery limit exceeded",
            {},
        ),
    ]
    for kind, reason, message, extra in artifact_vectors:
        record = {"kind": kind, "reason": reason, "message": message, "source": "input.md", **extra}
        assert artifact_input.is_valid(record), reason
        assert not artifact_input.is_valid({**record, "message": "parser prose"}), reason

    value_domain = {
        "kind": "parse_error",
        "reason": "value_domain",
        "message": "artifact contains a non-portable YAML value",
        "source": "input.md",
    }
    assert not artifact_input.is_valid(value_domain)


def test_runner_compares_json_without_python_boolean_number_coercion() -> None:
    assert _canonical_json(True) != _canonical_json(1)
    assert _canonical_json(False) != _canonical_json(0)
    assert _canonical_json({"year": True}) != _canonical_json({"year": 1})


def test_draft_release_schemas_keep_identity_and_digest_boundaries_separate() -> None:
    schemas = _load_schemas()
    registry = _registry(schemas)

    release_metadata = {
        "schema_version": "1",
        "release_state": "development",
        "logical_version": "0.2.2",
        "discovery_protocol": "1",
        "packages": {
            "python": {"name": "softschema", "version": "0.2.2", "pin": "0.2.2"},
            "npm": {"name": "softschema", "version": "0.2.2", "pin": "0.2.2"},
        },
        "conformance": {"version": "0.0.0-draft.1", "status": "candidate"},
        "runtimes": {
            "python": {"minimum": "3.11"},
            "node": {"minimum": "22.12"},
            "bun": {"minimum": "1.3.11"},
        },
        "expected_artifacts": ["softschema.whl"],
    }
    release_metadata_validator = Draft202012Validator(
        schemas["release-metadata.schema.json"], registry=registry
    )
    assert release_metadata_validator.is_valid(release_metadata)
    assert not release_metadata_validator.is_valid(
        {
            **release_metadata,
            "conformance": {
                "version": "0.0.0-draft.1",
                "status": "candidate",
                "sha256": "0" * 64,
            },
        }
    )
    assert not release_metadata_validator.is_valid(
        {**release_metadata, "expected_artifacts": ["../outside.whl"]}
    )

    subject = {
        "kind": "wheel",
        "media_type": "application/zip",
        "size": 42,
        "sha256": "0" * 64,
    }
    release_manifest = {
        "schema_version": "1",
        "logical_version": "0.2.2",
        "source_commit": "0" * 40,
        "subjects": {"softschema-0.2.2.whl": subject},
    }
    release_manifest_validator = Draft202012Validator(
        schemas["release-manifest.schema.json"], registry=registry
    )
    assert release_manifest_validator.is_valid(release_manifest)
    assert not release_manifest_validator.is_valid(
        {**release_manifest, "subjects": {"../softschema.whl": subject}}
    )

    public_claims = {
        "schema_version": "1",
        "claims": {
            "runtime.python.minimum": {
                "source": {"path": "release-metadata.json", "pointer": "/runtimes/python/minimum"},
                "targets": [{"path": "README.md", "marker": "runtime-python-minimum"}],
            }
        },
    }
    public_claims_validator = Draft202012Validator(
        schemas["public-claims.schema.json"], registry=registry
    )
    assert public_claims_validator.is_valid(public_claims)
    invalid_claims = {
        **public_claims,
        "claims": {
            "runtime.python.minimum": {
                "source": {"path": "arbitrary.json", "pointer": ""},
                "targets": [{"path": "README.md", "marker": "runtime-python-minimum"}],
            }
        },
    }
    assert not public_claims_validator.is_valid(invalid_claims)
    traversal_claims = {
        **public_claims,
        "claims": {
            "runtime.python.minimum": {
                "source": {"path": "release-metadata.json", "pointer": ""},
                "targets": [{"path": "../../outside.md", "marker": "runtime"}],
            }
        },
    }
    assert not public_claims_validator.is_valid(traversal_claims)


@pytest.mark.parametrize(
    "text",
    [
        '{"key": 1, "key": 2}',
        '{"value": NaN}',
        '{"value":"\\ud800"}',
        '{"\\udfff":true}',
    ],
)
def test_runner_rejects_non_strict_json(tmp_path: Path, text: str) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ConformanceError):
        _load_json(path)


def test_runner_uses_strict_json_for_runtime_output() -> None:
    with pytest.raises(ConformanceError):
        _parse_json('{"year": 1, "year": true}', "runtime stdout")


def test_runner_leaves_malformed_schema_syntax_to_the_selected_runtime(tmp_path: Path) -> None:
    schema = tmp_path / "malformed.schema.yaml"
    schema.write_text("properties: [\n", encoding="utf-8")
    _check_compiled_schema_digest(schema, "malformed schema")


def test_shared_runner_checks_foundation_and_executes_python_case() -> None:
    manifest = _load_yaml(MANIFEST)
    pending_case_ids = [
        entry["id"]
        for entry in (
            _load_yaml(CONFORMANCE / case_entry["path"]) for case_entry in manifest["cases"]
        )
        if entry["execution"]["status"] == "pending"
    ]
    expected_common = {
        "cases": len(manifest["cases"]),
        "ok": True,
        "pending_case_ids": pending_case_ids,
        "pending_cases": len(pending_case_ids),
        "ready_cases": len(manifest["cases"]) - len(pending_case_ids),
        "schemas": len(EXPECTED_SCHEMAS),
        "status": "draft",
        "vector_cases": sum(
            len(json.loads((CONFORMANCE / entry["path"]).read_text(encoding="utf-8"))["cases"])
            for entry in manifest["vector_suites"]
        ),
        "vector_suites": len(manifest["vector_suites"]),
    }
    check = subprocess.run(
        [sys.executable, "conformance/run.py", "--check-only", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert check.returncode == 0, check.stderr
    assert json.loads(check.stdout) == {**expected_common, "implementations": []}

    run = subprocess.run(
        [sys.executable, "conformance/run.py", "--implementation", "python", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout) == {**expected_common, "implementations": ["python"]}
