"""Draft conformance-kit integrity and runner tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from ruamel.yaml import YAML

from conformance.run import (
    ConformanceError,
    _canonical_json,
    _check_compiled_schema_digest,
    _load_json,
    _parse_json,
)

ROOT = Path(__file__).parents[3]
CONFORMANCE = ROOT / "conformance"
SCHEMAS = CONFORMANCE / "schemas"
MANIFEST = CONFORMANCE / "manifest.yaml"

EXPECTED_SCHEMAS = {
    "artifact-input-result-v1.schema.json",
    "build-metadata.schema.json",
    "case.schema.json",
    "compiled-schema-profile.schema.json",
    "doctor-result.schema.json",
    "manifest.schema.json",
    "metadata.schema.json",
    "public-claims.schema.json",
    "release-manifest.schema.json",
    "release-metadata.schema.json",
    "structural-error.schema.json",
    "validation-result-diagnostic-v1.schema.json",
    "validation-result-legacy.schema.json",
    "x-softschema.schema.json",
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
        expected_schema = schemas[case["expected"]["schema"]]
        validator = Draft202012Validator(expected_schema, registry=registry)
        assert list(validator.iter_errors(expected)) == []


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
        "artifact_formats": {"current": "legacy-0.2", "supported": ["legacy-0.2"]},
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


@pytest.mark.parametrize("text", ['{"key": 1, "key": 2}', '{"value": NaN}'])
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
