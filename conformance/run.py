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

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.exceptions import CannotDetermineSpecification, Unresolvable
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parent
MANIFEST_PATH = ROOT / "manifest.yaml"
SCHEMA_DIRECTORY = ROOT / "schemas"
TYPESCRIPT_CLI = REPOSITORY / "packages" / "typescript" / "dist" / "cli.js"
CASE_TIMEOUT_SECONDS = 30


class ConformanceError(RuntimeError):
    """A deterministic corpus-integrity or case-execution failure."""


@dataclass(frozen=True)
class Corpus:
    """Validated conformance inputs used by every implementation run."""

    manifest: dict[str, Any]
    schemas: dict[str, dict[str, Any]]
    registry: Registry[Any]
    cases: list[tuple[Path, dict[str, Any]]]


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

    return json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_constant,
    )


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


def load_corpus() -> Corpus:
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
        if expected_schema_name not in schemas:
            raise ConformanceError(
                f"{case['id']} names unknown expected schema {expected_schema_name}"
            )
        expected_path = _confined_file(case_directory, case["expected"]["result"]["path"])
        _assert_valid(
            _load_json(expected_path),
            schemas[expected_schema_name],
            registry,
            f"{case['id']} expected result",
        )
        cases.append((case_path, case))

    return Corpus(manifest=manifest, schemas=schemas, registry=registry, cases=cases)


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


def _case_arguments(case: dict[str, Any]) -> list[str]:
    if case["operation"] != "validate":
        raise ConformanceError(
            f"runner does not yet implement operation {case['operation']!r} for {case['id']}"
        )
    if case["inputs"]["resources"]:
        raise ConformanceError(f"runner does not yet implement explicit resources for {case['id']}")
    return [
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
        expected_schema = corpus.schemas[case["expected"]["schema"]]
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
    parser.add_argument("--json", action="store_true", help="Emit the summary as JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    requested = args.implementation or []
    if "all" in requested:
        implementations = ["python", "node", "bun"]
    else:
        implementations = list(dict.fromkeys(requested))
    if not args.check_only and not implementations:
        _parser().error("pass --check-only or at least one --implementation")

    try:
        corpus = load_corpus()
        for implementation in implementations:
            run_implementation(corpus, implementation)
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
