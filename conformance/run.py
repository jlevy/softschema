"""Validate and execute the draft language-neutral conformance corpus."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft4Validator, Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.exceptions import CannotDetermineSpecification, Unresolvable
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parent
MANIFEST_PATH = ROOT / "manifest.yaml"
INTEGRITY_LOCK_PATH = ROOT / "manifest.lock.json"
SCHEMA_DIRECTORY = ROOT / "schemas"
TYPESCRIPT_CLI = REPOSITORY / "packages" / "typescript" / "dist" / "cli.js"
PYTHON_ADAPTER = ROOT / "adapters" / "python_adapter.py"
JAVASCRIPT_ADAPTER = ROOT / "adapters" / "javascript-adapter.mjs"
TYPESCRIPT_NODE_ENTRY = REPOSITORY / "packages" / "typescript" / "dist" / "node.js"
TYPESCRIPT_CORE_ENTRY = REPOSITORY / "packages" / "typescript" / "dist" / "core" / "index.js"
TYPESCRIPT_YAML_ENTRY = TYPESCRIPT_NODE_ENTRY
CASE_TIMEOUT_SECONDS = 30
INTEGRITY_LOCK_FORMAT = "softschema-conformance-integrity-v1"


class ConformanceError(RuntimeError):
    """A deterministic corpus-integrity or case-execution failure."""


@dataclass(frozen=True)
class Corpus:
    """Validated conformance inputs used by every implementation run."""

    manifest: dict[str, Any]
    schemas: dict[str, dict[str, Any]]
    registry: Registry[Any]
    cases: list[tuple[Path, dict[str, Any]]]
    vector_suites: list[tuple[Path, dict[str, Any]]]
    artifacts: list[Path]
    archive_files: tuple[Path, ...]


def _load_yaml(path: Path) -> Any:
    parser = YAML(typ="safe")
    parser.allow_duplicate_keys = False
    return parser.load(path)


def _parse_json(text: str, label: str) -> Any:
    """Parse strict JSON without duplicate keys or JavaScript-only numeric constants."""

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ConformanceError(f"{label}: duplicate JSON key {key!r}")
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ConformanceError(f"{label}: non-finite JSON number {value}")

    value = json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_constant,
    )
    _validate_json_unicode(value, label)
    return value


def _validate_json_unicode(value: Any, label: str) -> None:
    """Reject escaped lone surrogates before comparison or serialization."""
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, str):
            try:
                current.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise ConformanceError(f"{label}: invalid Unicode scalar value in JSON") from exc
        elif isinstance(current, dict):
            for key in current:
                try:
                    key.encode("utf-8", errors="strict")
                except UnicodeEncodeError as exc:
                    raise ConformanceError(f"{label}: invalid Unicode scalar key in JSON") from exc
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def _load_json(path: Path) -> Any:
    return _parse_json(path.read_text(encoding="utf-8"), str(path))


def _canonical_json(value: Any) -> str:
    """Serialize a JSON value so comparison preserves booleans and numeric spellings."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _check_vector_case_ids(suite: dict[str, Any]) -> None:
    """Enforce projected case-ID uniqueness that JSON Schema cannot express."""
    case_ids: set[str] = set()
    for case in suite["cases"]:
        case_id = case["id"]
        if case_id in case_ids:
            raise ConformanceError(f"duplicate vector case id: {suite['id']}/{case_id}")
        case_ids.add(case_id)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _confined_file(base: Path, relative_path: str) -> Path:
    candidate = (base / relative_path).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as exc:
        raise ConformanceError(f"path escapes conformance root: {relative_path}") from exc
    if not candidate.is_file():
        raise ConformanceError(f"declared file does not exist: {relative_path}")
    return candidate


def _assert_valid(
    value: Any,
    schema: dict[str, Any],
    registry: Registry[Any],
    label: str,
) -> None:
    try:
        errors = sorted(
            Draft202012Validator(schema, registry=registry).iter_errors(value),
            key=lambda error: ([str(part) for part in error.absolute_path], error.message),
        )
    except Exception as exc:
        if exc.__class__.__module__.startswith(("jsonschema", "referencing")):
            raise ConformanceError(f"{label} contains an unresolved schema reference") from exc
        raise
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise ConformanceError(f"{label} is invalid at {location}: {first.message}")


def _check_digest(path: Path, expected: str, label: str) -> None:
    actual = _digest(path)
    if actual != expected:
        raise ConformanceError(f"{label} digest mismatch: expected {expected}, got {actual}")


def _check_compiled_schema_digest(path: Path, label: str) -> None:
    """Verify the compiler hash when a case schema declares one."""
    try:
        schema = _load_yaml(path)
    except YAMLError:
        # Malformed-schema cases authenticate their raw bytes through the case digest.
        # The selected implementation, not the harness, owns their structured failure.
        return
    if not isinstance(schema, dict):
        return
    metadata = schema.get("x-softschema")
    if not isinstance(metadata, dict) or "schema_sha256" not in metadata:
        return
    declared = metadata["schema_sha256"]
    if not isinstance(declared, str):
        raise ConformanceError(f"{label} x-softschema.schema_sha256 must be a string")
    hash_input = copy.deepcopy(schema)
    del hash_input["x-softschema"]["schema_sha256"]
    actual = hashlib.sha256(_canonical_json(hash_input).encode("utf-8")).hexdigest()
    if actual != declared:
        raise ConformanceError(
            f"{label} compiler digest mismatch: expected {declared}, got {actual}"
        )


def _select_schema(
    schemas: dict[str, dict[str, Any]],
    reference: str,
) -> dict[str, Any]:
    name, separator, fragment = reference.partition("#")
    if name not in schemas:
        raise ConformanceError(f"unknown expected schema {reference}")
    selected: Any = schemas[name]
    if separator:
        if fragment == "":
            return selected
        if not fragment.startswith("/"):
            raise ConformanceError(f"unsupported expected schema fragment {reference}")
        schema_id = selected.get("$id")
        if not isinstance(schema_id, str):
            raise ConformanceError(f"expected schema has no identifier: {name}")
        return {"$ref": f"{schema_id}#{fragment}"}
    if not isinstance(selected, dict):
        raise ConformanceError(f"expected schema fragment is not an object: {reference}")
    return selected


def _archive_file_set(
    cases: list[tuple[Path, dict[str, Any]]],
    schemas: dict[str, dict[str, Any]],
    vector_suites: list[tuple[Path, dict[str, Any]]],
    artifacts: list[Path],
) -> set[Path]:
    files = {
        ROOT / "README.md",
        ROOT / "WALKTHROUGH.md",
        ROOT / "consumer.py",
        ROOT / "publication.py",
        ROOT / "run.py",
        MANIFEST_PATH,
        *artifacts,
        *(SCHEMA_DIRECTORY / name for name in schemas),
        *(path for path, _suite in vector_suites),
    }
    for case_path, case in cases:
        files.add(case_path)
        case_directory = case_path.parent
        references = [
            case["inputs"]["artifact"],
            case["inputs"]["schema"],
            case["expected"]["result"],
            *[resource["file"] for resource in case["inputs"]["resources"]],
        ]
        files.update(case_directory / reference["path"] for reference in references)
    return files


def build_integrity_lock(corpus: Corpus) -> dict[str, Any]:
    """Build the non-self-referential file inventory used by kit-only consumers."""
    entries = []
    for path in corpus.archive_files:
        relative = path.relative_to(REPOSITORY).as_posix()
        entries.append(
            {
                "path": relative,
                "sha256": _digest(path),
                "size": path.stat().st_size,
            }
        )
    return {
        "format": INTEGRITY_LOCK_FORMAT,
        "kit_version": corpus.manifest["kit_version"],
        "files": entries,
    }


def _check_integrity_lock(corpus: Corpus) -> None:
    if not INTEGRITY_LOCK_PATH.is_file():
        raise ConformanceError("missing conformance integrity lock: manifest.lock.json")
    actual = _load_json(INTEGRITY_LOCK_PATH)
    expected = build_integrity_lock(corpus)
    if _canonical_json(actual) != _canonical_json(expected):
        raise ConformanceError(
            "manifest.lock.json is stale; regenerate it from the validated corpus"
        )


def load_corpus(*, check_lock: bool = True) -> Corpus:
    """Load and fully integrity-check the draft schemas, manifest, and cases."""
    schemas = {
        path.name: _load_json(path) for path in sorted(SCHEMA_DIRECTORY.glob("*.schema.json"))
    }
    if not schemas:
        raise ConformanceError("no conformance schemas found")

    registry: Registry[Any] = Registry()
    schema_ids: set[str] = set()
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id.startswith(
            "urn:softschema:draft:conformance:"
        ):
            raise ConformanceError(f"{name} has no draft conformance $id")
        if schema_id in schema_ids:
            raise ConformanceError(f"duplicate schema $id: {schema_id}")
        schema_ids.add(schema_id)
        registry = registry.with_resource(schema_id, Resource.from_contents(schema))

    manifest = _load_yaml(MANIFEST_PATH)
    if not isinstance(manifest, dict):
        raise ConformanceError("manifest root must be a mapping")
    _assert_valid(manifest, schemas["manifest.schema.json"], registry, "manifest")

    listed_names: set[str] = set()
    listed_ids: set[str] = set()
    listed_paths: set[Path] = set()
    for entry in manifest["schemas"]:
        path = _confined_file(ROOT, entry["path"])
        expected_path = (SCHEMA_DIRECTORY / path.name).resolve()
        if path != expected_path:
            raise ConformanceError(
                f"manifest schema path must be schemas/{path.name}: {entry['path']}"
            )
        if path in listed_paths:
            raise ConformanceError(f"duplicate manifest schema path: {entry['path']}")
        if entry["id"] in listed_ids:
            raise ConformanceError(f"duplicate manifest schema id: {entry['id']}")
        listed_paths.add(path)
        listed_ids.add(entry["id"])
        _check_digest(path, entry["sha256"], entry["path"])
        schema = _load_json(path)
        if schema.get("$id") != entry["id"]:
            raise ConformanceError(f"{entry['path']} $id does not match manifest")
        listed_names.add(path.name)
    if listed_names != set(schemas):
        missing = sorted(set(schemas) - listed_names)
        extra = sorted(listed_names - set(schemas))
        raise ConformanceError(
            f"manifest schema inventory mismatch: missing={missing}, extra={extra}"
        )

    cases: list[tuple[Path, dict[str, Any]]] = []
    case_ids: set[str] = set()
    case_paths: set[Path] = set()
    case_schema = schemas["case.schema.json"]
    for entry in manifest["cases"]:
        case_path = _confined_file(ROOT, entry["path"])
        if case_path in case_paths:
            raise ConformanceError(f"duplicate manifest case path: {entry['path']}")
        case_paths.add(case_path)
        _check_digest(case_path, entry["sha256"], entry["path"])
        case = _load_yaml(case_path)
        _assert_valid(case, case_schema, registry, entry["path"])
        if case["id"] != entry["id"]:
            raise ConformanceError(f"{entry['path']} id does not match manifest")
        if case["id"] in case_ids:
            raise ConformanceError(f"duplicate case id: {case['id']}")
        case_ids.add(case["id"])

        case_directory = case_path.parent
        file_refs = [
            case["inputs"]["artifact"],
            case["inputs"]["schema"],
            case["expected"]["result"],
            *[resource["file"] for resource in case["inputs"]["resources"]],
        ]
        for file_ref in file_refs:
            referenced = _confined_file(case_directory, file_ref["path"])
            _check_digest(referenced, file_ref["sha256"], f"{case['id']}/{file_ref['path']}")
        schema_path = _confined_file(case_directory, case["inputs"]["schema"]["path"])
        _check_compiled_schema_digest(schema_path, f"{case['id']}/{schema_path.name}")

        expected_schema_name = case["expected"]["schema"]
        expected_schema = _select_schema(schemas, expected_schema_name)
        expected_path = _confined_file(case_directory, case["expected"]["result"]["path"])
        _assert_valid(
            _load_json(expected_path),
            expected_schema,
            registry,
            f"{case['id']} expected result",
        )
        cases.append((case_path, case))

    vector_suites: list[tuple[Path, dict[str, Any]]] = []
    vector_ids: set[str] = set()
    vector_schema = schemas["vector-suite.schema.json"]
    for entry in manifest["vector_suites"]:
        path = _confined_file(ROOT, entry["path"])
        _check_digest(path, entry["sha256"], entry["path"])
        suite = _load_json(path)
        _assert_valid(suite, vector_schema, registry, entry["path"])
        if suite["id"] != entry["id"]:
            raise ConformanceError(f"{entry['path']} id does not match manifest")
        if suite["id"] in vector_ids:
            raise ConformanceError(f"duplicate vector suite id: {suite['id']}")
        vector_ids.add(suite["id"])
        _check_vector_case_ids(suite)
        if suite["operation"] == "canonicalize":
            for vector in suite["cases"]:
                raw_schema = vector["input"].get("schema")
                _assert_valid(
                    raw_schema,
                    schemas["compiler-input-profile.schema.json"],
                    registry,
                    f"{suite['id']}/{vector['id']} compiler input",
                )
                try:
                    Draft202012Validator.check_schema(raw_schema)
                except SchemaError as exc:
                    raise ConformanceError(
                        f"{suite['id']}/{vector['id']} is not a Draft 2020-12 schema"
                    ) from exc
        if suite["operation"] == "validate-structural":
            for vector in suite["cases"]:
                inputs = vector["input"]
                bundle = {
                    "root": inputs.get("schema"),
                    "resources": inputs.get("resources", {}),
                }
                _assert_valid(
                    bundle,
                    schemas["resource-bundle.schema.json"],
                    registry,
                    f"{suite['id']}/{vector['id']} resource bundle",
                )
        if suite["operation"] == "diagnostic-summary":
            result_schema = _select_schema(
                schemas, "validation-result-diagnostic-v1.schema.json#/$defs/result"
            )
            for vector in suite["cases"]:
                for index, result in enumerate(vector["input"].get("results", [])):
                    _assert_valid(
                        result,
                        result_schema,
                        registry,
                        f"{suite['id']}/{vector['id']} result {index}",
                    )
        vector_suites.append((path, suite))

    artifacts: list[Path] = []
    artifact_ids: set[str] = set()
    for entry in manifest["artifacts"]:
        path = _confined_file(ROOT, entry["path"])
        _check_digest(path, entry["sha256"], entry["path"])
        if entry["id"] in artifact_ids:
            raise ConformanceError(f"duplicate artifact id: {entry['id']}")
        artifact_ids.add(entry["id"])
        if "schema" in entry:
            schema_name = entry["schema"]
            if schema_name not in schemas:
                raise ConformanceError(f"{entry['id']} names unknown schema {schema_name}")
            _assert_valid(_load_json(path), schemas[schema_name], registry, entry["path"])
        if entry["role"] == "vendor-schema":
            vendor_schema = _load_json(path)
            try:
                Draft4Validator.check_schema(vendor_schema)
            except SchemaError as exc:
                raise ConformanceError(f"{entry['path']} is not a valid Draft-04 schema") from exc
        artifacts.append(path)

    known_coverage = {
        *(f"case:{case['id']}" for _path, case in cases),
        *(f"suite:{suite['id']}" for _path, suite in vector_suites),
        *(f"schema:{name}" for name in schemas),
        *(f"artifact:{entry['id']}" for entry in manifest["artifacts"]),
    }
    for family, references in manifest["coverage"].items():
        for reference in references:
            if reference not in known_coverage:
                raise ConformanceError(f"coverage {family} names unknown target {reference}")

    archive_files = _archive_file_set(cases, schemas, vector_suites, artifacts)
    for path in archive_files:
        if path.is_symlink() or not path.is_file():
            raise ConformanceError(f"archive closure contains an unsafe file: {path}")
    corpus = Corpus(
        manifest=manifest,
        schemas=schemas,
        registry=registry,
        cases=cases,
        vector_suites=vector_suites,
        artifacts=artifacts,
        archive_files=tuple(
            sorted(archive_files, key=lambda path: path.relative_to(REPOSITORY).as_posix())
        ),
    )
    if check_lock:
        _check_integrity_lock(corpus)
    return corpus


def _implementation_command(implementation: str) -> list[str]:
    if implementation == "python":
        return [sys.executable, "-m", "softschema.cli"]
    if not TYPESCRIPT_CLI.is_file():
        raise ConformanceError(
            "TypeScript CLI is not built; run `cd packages/typescript && bun run build`"
        )
    executable = shutil.which(implementation)
    if executable is None:
        raise ConformanceError(f"required runtime is not on PATH: {implementation}")
    return [executable, str(TYPESCRIPT_CLI)]


def _adapter_command(implementation: str) -> list[str]:
    if implementation == "python":
        return [sys.executable, str(PYTHON_ADAPTER)]
    executable = shutil.which(implementation)
    if executable is None:
        raise ConformanceError(f"required runtime is not on PATH: {implementation}")
    required = [
        JAVASCRIPT_ADAPTER,
        TYPESCRIPT_NODE_ENTRY,
        TYPESCRIPT_CORE_ENTRY,
        TYPESCRIPT_YAML_ENTRY,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ConformanceError(f"TypeScript vector adapter is not built: {missing}")
    return [executable, *(str(path) for path in required)]


def _case_arguments(case: dict[str, Any]) -> list[str]:
    if case["operation"] != "validate":
        raise ConformanceError(
            f"runner does not yet implement operation {case['operation']!r} for {case['id']}"
        )
    if case["inputs"]["resources"]:
        raise ConformanceError(f"runner does not yet implement explicit resources for {case['id']}")
    arguments = [
        "validate",
        case["inputs"]["artifact"]["path"],
        "--schema",
        case["inputs"]["schema"]["path"],
        "--contract",
        case["options"]["contract"],
        "--envelope",
        case["options"]["envelope"],
        "--status",
        case["options"]["status"],
    ]
    profile = case["options"].get("profile")
    if profile is not None:
        arguments.extend(["--profile", profile])
    output_format = case["options"].get("output_format")
    if output_format is not None:
        arguments.extend(["--format", output_format])
    return arguments


def run_implementation(corpus: Corpus, implementation: str) -> None:
    """Execute every case against one runtime and compare its exact JSON value."""
    base_command = _implementation_command(implementation)
    for case_path, case in corpus.cases:
        if case["execution"]["status"] == "pending":
            continue
        case_directory = case_path.parent
        try:
            process = subprocess.run(
                [*base_command, *_case_arguments(case)],
                cwd=case_directory,
                text=True,
                encoding="utf-8",
                errors="strict",
                capture_output=True,
                check=False,
                timeout=CASE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise ConformanceError(
                f"{implementation}/{case['id']} exceeded {CASE_TIMEOUT_SECONDS}s"
            ) from exc
        expected_exit = case["expected"]["exit_code"]
        if process.returncode != expected_exit:
            raise ConformanceError(
                f"{implementation}/{case['id']} exited {process.returncode}, "
                f"expected {expected_exit}: {process.stderr.strip()}"
            )
        if process.stderr:
            raise ConformanceError(
                f"{implementation}/{case['id']} wrote unexpected stderr: {process.stderr.strip()}"
            )
        try:
            actual = _parse_json(process.stdout, f"{implementation}/{case['id']} stdout")
        except json.JSONDecodeError as exc:
            raise ConformanceError(
                f"{implementation}/{case['id']} did not emit one JSON value"
            ) from exc

        expected_path = _confined_file(case_directory, case["expected"]["result"]["path"])
        expected = _load_json(expected_path)
        expected_schema = _select_schema(corpus.schemas, case["expected"]["schema"])
        _assert_valid(
            actual,
            expected_schema,
            corpus.registry,
            f"{implementation}/{case['id']} result",
        )
        if _canonical_json(actual) != _canonical_json(expected):
            raise ConformanceError(
                f"{implementation}/{case['id']} result differs from {expected_path.name}"
            )


def run_vector_suites(corpus: Corpus, implementation: str) -> None:
    """Execute every portable-core suite through one runtime's JSON adapter."""
    command = _adapter_command(implementation)
    for _path, suite in corpus.vector_suites:
        try:
            process = subprocess.run(
                command,
                input=_canonical_json(suite),
                text=True,
                encoding="utf-8",
                errors="strict",
                capture_output=True,
                check=False,
                timeout=CASE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise ConformanceError(
                f"{implementation}/{suite['id']} exceeded {CASE_TIMEOUT_SECONDS}s"
            ) from exc
        if process.returncode != 0:
            raise ConformanceError(
                f"{implementation}/{suite['id']} adapter exited {process.returncode}: "
                f"{process.stderr.strip()}"
            )
        if process.stderr:
            raise ConformanceError(
                f"{implementation}/{suite['id']} adapter wrote stderr: {process.stderr.strip()}"
            )
        try:
            actual = _parse_json(process.stdout, f"{implementation}/{suite['id']} stdout")
        except json.JSONDecodeError as exc:
            raise ConformanceError(
                f"{implementation}/{suite['id']} adapter did not emit one JSON value"
            ) from exc
        if not isinstance(actual, dict):
            raise ConformanceError(f"{implementation}/{suite['id']} result is not an object")
        if actual.get("format") != "softschema-vector-results-v1":
            raise ConformanceError(f"{implementation}/{suite['id']} has wrong adapter format")
        if actual.get("id") != suite["id"]:
            raise ConformanceError(f"{implementation}/{suite['id']} has wrong suite id")
        expected_results = [
            {"id": case["id"], "actual": case["expected"]} for case in suite["cases"]
        ]
        if _canonical_json(actual.get("results")) != _canonical_json(expected_results):
            raise ConformanceError(
                f"{implementation}/{suite['id']} vector results differ from expected values"
            )


def check_doctor_claims(corpus: Corpus, implementation: str) -> None:
    """Validate discovery output and cross-check kit-owned capability claims."""
    process = subprocess.run(
        [*_implementation_command(implementation), "doctor", "--json"],
        cwd=REPOSITORY,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        check=False,
        timeout=CASE_TIMEOUT_SECONDS,
    )
    if process.returncode != 0 or process.stderr:
        raise ConformanceError(
            f"{implementation}/doctor failed: {process.stderr.strip() or process.returncode}"
        )
    try:
        report = _parse_json(process.stdout, f"{implementation}/doctor stdout")
    except json.JSONDecodeError as exc:
        raise ConformanceError(f"{implementation}/doctor did not emit strict JSON") from exc
    _assert_valid(
        report,
        corpus.schemas["doctor-result.schema.json"],
        corpus.registry,
        f"{implementation}/doctor",
    )
    if report["runtime"]["name"] != implementation:
        raise ConformanceError(f"{implementation}/doctor reports the wrong runtime")
    capabilities = report["capabilities"]
    if set(capabilities["artifact_formats"]) != set(corpus.manifest["artifact_formats"]):
        raise ConformanceError(f"{implementation}/doctor artifact formats differ from manifest")
    conformance = capabilities["conformance"]
    if conformance != {"version": corpus.manifest["kit_version"], "status": "unavailable"}:
        raise ConformanceError(f"{implementation}/doctor conformance claim differs from manifest")
    required_operations = {case["operation"] for _path, case in corpus.cases}
    if not required_operations.issubset(capabilities["operations"]):
        raise ConformanceError(f"{implementation}/doctor omits a case operation")
    requested_formats = {
        case["options"].get("output_format", "json") for _path, case in corpus.cases
    }
    if not requested_formats.issubset(capabilities["output_formats"]):
        raise ConformanceError(f"{implementation}/doctor omits a conformance output format")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and run the draft softschema conformance corpus."
    )
    parser.add_argument(
        "--implementation",
        action="append",
        choices=["python", "node", "bun", "all"],
        help="Runtime to execute; repeat the flag or use all.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate schemas, paths, digests, descriptors, and expected results only.",
    )
    parser.add_argument(
        "--write-lock",
        action="store_true",
        help="Regenerate manifest.lock.json after validating every declared digest.",
    )
    parser.add_argument("--json", action="store_true", help="Emit the summary as JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    requested = args.implementation or []
    if "all" in requested:
        implementations = ["python", "node", "bun"]
    else:
        implementations = list(dict.fromkeys(requested))
    if args.write_lock and (args.check_only or implementations):
        _parser().error("--write-lock cannot be combined with execution flags")
    if not args.check_only and not args.write_lock and not implementations:
        _parser().error("pass --check-only or at least one --implementation")

    try:
        corpus = load_corpus(check_lock=not args.write_lock)
        if args.write_lock:
            INTEGRITY_LOCK_PATH.write_text(
                json.dumps(
                    build_integrity_lock(corpus),
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                    allow_nan=False,
                )
                + "\n",
                encoding="utf-8",
            )
            print(f"wrote {INTEGRITY_LOCK_PATH.relative_to(REPOSITORY)}")
            return 0
        for implementation in implementations:
            check_doctor_claims(corpus, implementation)
            run_implementation(corpus, implementation)
            run_vector_suites(corpus, implementation)
    except (
        CannotDetermineSpecification,
        ConformanceError,
        OSError,
        SchemaError,
        ValueError,
        YAMLError,
        Unresolvable,
    ) as exc:
        print(f"softschema conformance: {exc}", file=sys.stderr)
        return 1

    pending_case_ids = [
        case["id"] for _path, case in corpus.cases if case["execution"]["status"] == "pending"
    ]
    summary = {
        "cases": len(corpus.cases),
        "implementations": implementations,
        "ok": True,
        "pending_case_ids": pending_case_ids,
        "pending_cases": len(pending_case_ids),
        "ready_cases": len(corpus.cases) - len(pending_case_ids),
        "schemas": len(corpus.schemas),
        "status": corpus.manifest["status"],
        "vector_cases": sum(len(suite["cases"]) for _path, suite in corpus.vector_suites),
        "vector_suites": len(corpus.vector_suites),
    }
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        selected = ", ".join(implementations) if implementations else "integrity only"
        print(
            f"draft conformance passed: {len(corpus.schemas)} schemas, "
            f"{summary['ready_cases']} ready cases, {summary['pending_cases']} pending, {selected}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
