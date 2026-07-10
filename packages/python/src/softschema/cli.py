"""Command-line interface for softschema."""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import sys
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from importlib import resources
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any, cast

from frontmatter_format import FmFormatError
from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAMLError

from softschema.compile import compile_model
from softschema.errors import canonical_number
from softschema.generate import regenerate
from softschema.models import (
    Contract,
    SchemaProfile,
    SchemaStatus,
    parse_schema_metadata,
    validate_contract_id,
    validate_schema_id,
)
from softschema.skill_installer import (
    InstallRequest,
    SkillInstallUsageError,
    execute_skill_install,
    format_install_plan_text,
)
from softschema.validate import (
    EnvelopeAmbiguityError,
    artifact_error_record,
    infer_envelope_key,
    read_frontmatter,
    read_yaml_artifact,
    validate_artifact,
)

BRIEF_MARKER_START = "<!-- BEGIN SOFTSCHEMA BRIEF -->"
BRIEF_MARKER_END = "<!-- END SOFTSCHEMA BRIEF -->"
DOCTOR_OPERATIONS: tuple[str, ...] = (
    "compile",
    "docs",
    "doctor",
    "generate",
    "inspect",
    "prime",
    "skill",
    "validate",
)
DOCTOR_OUTPUT_FORMATS: tuple[str, ...] = ("json", "text")


class UsageError(ValueError):
    """A user/input mistake: bad flags, a bad model spec, or an unusable document.

    Subclasses ``ValueError`` so it is reported through the CLI's user-error boundary
    (clean one-line message, exit 2) and so library callers that already catch
    ``ValueError`` keep working.
    """


# Exit codes: 0 ok, 1 validation failure or drift (``--check``), 2 user/usage error.
# The families below are user mistakes (bad files, bad input, bad config), caught by the
# per-subcommand error boundary so an ordinary mistake never prints a traceback.
# ``TypeError`` and ``KeyError`` are deliberately excluded: nothing in the package raises
# them for user input, so they only ever signal an internal bug and must surface as a
# traceback rather than be masked as a clean exit 2.
_USER_ERRORS = (
    OSError,
    FmFormatError,
    YAMLError,
    ModuleNotFoundError,
    ImportError,
    ValidationError,
    ValueError,
)


@dataclass(frozen=True)
class ResourceTopic:
    title: str
    path: str
    summary: str


DOC_TOPICS: dict[str, ResourceTopic] = {
    "readme": ResourceTopic("README", "README.md", "Short first-visitor overview."),
    "guide": ResourceTopic(
        "softschema Guide",
        "docs/softschema-guide.md",
        "Concepts, mental model, and adoption path.",
    ),
    "spec": ResourceTopic(
        "softschema Spec",
        "docs/softschema-spec.md",
        "Language-neutral artifact format.",
    ),
    "python-design": ResourceTopic(
        "Python Package Design",
        "docs/softschema-python-design.md",
        "Python package design decisions.",
    ),
    "typescript-design": ResourceTopic(
        "TypeScript Package Design",
        "docs/softschema-typescript-design.md",
        "TypeScript package design decisions.",
    ),
    "development": ResourceTopic(
        "Development",
        "docs/development.md",
        "Local development workflow.",
    ),
    "installation": ResourceTopic(
        "Installation",
        "docs/installation.md",
        "Installing softschema for Node or Python.",
    ),
    "example": ResourceTopic(
        "Movie Page Example",
        "examples/movie_page/README.md",
        "Copyable example overview.",
    ),
    "example-artifact": ResourceTopic(
        "Movie Page Artifact",
        "examples/movie_page/spirited-away.md",
        "Copyable Markdown/YAML artifact.",
    ),
    "example-model": ResourceTopic(
        "Movie Page Model",
        "examples/movie_page/model.py",
        "Pydantic model used by the example.",
    ),
    "example-host": ResourceTopic(
        "Movie Page Host Integration",
        "examples/movie_page/host_integration.py",
        "Host registry and validation helper.",
    ),
    "example-schema": ResourceTopic(
        "Movie Page Compiled Schema",
        "examples/movie_page/movie-page.schema.yaml",
        "Compiled JSON Schema for the example.",
    ),
    "skill": ResourceTopic(
        "softschema Skill",
        "skills/softschema/SKILL.md",
        "Portable agent skill instructions.",
    ),
}
# `agents` (AGENTS.md) and `publishing` (release runbook) are intentionally not bundled
# topics: both are repo/maintainer-internal and have no use inside an installed package.


def _run_cmd(command_name: str, func: Any, args: argparse.Namespace) -> int:
    """Run a subcommand handler inside an error boundary.

    Exceptions in ``_USER_ERRORS`` are reported to stderr as a one-line
    message (no traceback) and the process exits 2.  Any narrower try/except
    inside the handler still fires first.
    """
    try:
        return func(args)
    except _USER_ERRORS as exc:
        print(f"softschema {command_name}: {exc}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="softschema",
        description="Validate and explain soft schema Markdown/YAML artifacts.",
        epilog=_agent_help_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_installed_version()}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help=(
            "Validate an artifact. A self-describing artifact (softschema.contract, "
            "schema, envelope) needs no flags; flags override the document."
        ),
    )
    validate_parser.add_argument("path", type=Path)
    validate_parser.add_argument(
        "--profile",
        choices=[profile.value for profile in SchemaProfile],
        default=SchemaProfile.frontmatter_md.value,
        help="Artifact storage profile (default: frontmatter-md).",
    )
    validate_parser.add_argument("--contract", help="Override the document contract ID.")
    validate_parser.add_argument(
        "--envelope",
        help="Override the envelope key (softschema.envelope or single-key inference).",
    )
    validate_parser.add_argument(
        "--model",
        help=(
            "Pydantic model as module:Class for semantic validation. Optional. "
            "Imports and runs local code; use only with trusted models."
        ),
    )
    validate_parser.add_argument(
        "--schema",
        type=Path,
        help=(
            "Compiled JSON Schema (YAML or JSON). Optional override; without it the "
            "document's softschema.schema binding is used when present."
        ),
    )
    validate_parser.add_argument(
        "--status",
        choices=[status.value for status in SchemaStatus],
        help="Override the document status.",
    )
    validate_parser.set_defaults(func=_validate_cmd)

    compile_parser = subparsers.add_parser("compile", help="Compile a Pydantic model.")
    compile_parser.add_argument("model", help="Pydantic model as module:Class.")
    compile_parser.add_argument(
        "--out", required=True, type=Path, help="Output path for the compiled schema."
    )
    compile_parser.add_argument(
        "--contract",
        help="Required logical contract ID stored in x-softschema.contract.",
    )
    compile_parser.add_argument(
        "--schema-id",
        help="Canonical absolute HTTPS or URN identifier stored in JSON Schema $id.",
    )
    compile_parser.add_argument(
        "--check", action="store_true", help="Do not write; exit 1 on drift."
    )
    compile_parser.set_defaults(func=_compile_cmd)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect artifact metadata.")
    inspect_parser.add_argument("path", type=Path)
    inspect_parser.set_defaults(func=_inspect_cmd)

    docs_parser = subparsers.add_parser("docs", help="Print bundled docs and examples.")
    docs_parser.add_argument("topic", nargs="?", choices=sorted(DOC_TOPICS))
    docs_parser.add_argument(
        "--list",
        dest="list_topics",
        action="store_true",
        help="List bundled documentation topics.",
    )
    docs_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit topic metadata, and document content when a topic is selected, as JSON.",
    )
    docs_parser.set_defaults(func=_docs_cmd)

    generate_parser = subparsers.add_parser(
        "generate",
        help="Regenerate `softschema:generated` Markdown sections from schemas.",
    )
    generate_parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Markdown files containing softschema:generated markers.",
    )
    generate_parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if any section is stale.",
    )
    generate_parser.set_defaults(func=_generate_cmd)

    prime_parser = subparsers.add_parser(
        "prime",
        help="Print the full agent context: skill rules and the bundled docs index.",
    )
    prime_parser.set_defaults(func=_prime_cmd)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Report the versioned discovery protocol and runtime capabilities.",
    )
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the environment report as JSON.",
    )
    doctor_parser.set_defaults(func=_doctor_cmd)

    skill_parser = subparsers.add_parser("skill", help="Print agent-facing guidance.")
    skill_parser.add_argument(
        "--brief",
        action="store_true",
        help="Print compact skill guidance for constrained contexts.",
    )
    skill_parser.add_argument(
        "--install",
        action="store_true",
        help="Install the bundled skill after scope and ownership preflight.",
    )
    scope_group = skill_parser.add_mutually_exclusive_group()
    scope_group.add_argument(
        "--project",
        action="store_true",
        help="Install into a project target (explicitly permits --dir).",
    )
    scope_group.add_argument(
        "--global",
        dest="global_scope",
        action="store_true",
        help="Install into selected agents' personal skill roots.",
    )
    skill_parser.add_argument(
        "--dir",
        type=Path,
        help="Project directory to resolve; requires explicit --project.",
    )
    selector_group = skill_parser.add_mutually_exclusive_group()
    selector_group.add_argument(
        "--agent",
        action="append",
        default=[],
        metavar="NAME",
        help="Install only the named agent target; repeat for multiple agents.",
    )
    selector_group.add_argument(
        "--all-agents",
        action="store_true",
        help="Install all nine supported agent targets.",
    )
    skill_parser.add_argument(
        "--no-repo-check",
        action="store_true",
        help="Permit an explicit project destination outside Git.",
    )
    skill_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the complete plan without creating any filesystem entry.",
    )
    output_group = skill_parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Emit the install plan as JSON (the compatibility default).",
    )
    output_group.add_argument(
        "--text",
        action="store_true",
        help="Emit the install plan as stable human-readable text.",
    )
    skill_parser.set_defaults(func=_skill_cmd)

    args = parser.parse_args(argv)
    return _run_cmd(args.command, args.func, args)


def _validate_cmd(args: argparse.Namespace) -> int:
    # Without --model/--schema this is a metadata-only check: frontmatter parses,
    # the softschema: block is well-formed, and the envelope resolves; structural
    # and semantic layers are reported as skipped. Useful from the `soft` stage on.
    # Validate an explicit identity before reading a document or importing local code.
    if args.contract is not None:
        validate_contract_id(args.contract)
    # Read the document once here; both binding inference and validate_artifact reuse
    # the normalized root. Readable parse failures are validation results (exit 1),
    # while access failures remain exit 2.
    profile = SchemaProfile(args.profile)
    try:
        if profile == SchemaProfile.pure_yaml:
            parsed_root: Any = read_yaml_artifact(args.path)
        else:
            _content, parsed_root = read_frontmatter(args.path)
    except Exception as exc:
        record = artifact_error_record(args.path, exc)
        if record is None:
            raise
        print(_json(record))
        return 2 if record["kind"] == "input_error" else 1
    contract_id, status, envelope_key = _infer_validation_binding(args, parsed_root, profile)
    model = _load_model(args.model) if args.model else None
    contract = Contract(
        id=contract_id,
        model=model,
        envelope_key=envelope_key,
        schema_path=args.schema,
        status=status,
        profile=profile,
    )
    result = validate_artifact(args.path, contract=contract, frontmatter=parsed_root)
    print(_json(result))
    return 0 if result.ok else 1


def _infer_validation_binding(
    args: argparse.Namespace,
    frontmatter: Any,
    profile: SchemaProfile = SchemaProfile.frontmatter_md,
) -> tuple[str, SchemaStatus, str | None]:
    if not isinstance(frontmatter, dict):
        if args.contract is None:
            raise UsageError("missing --contract because the document has no YAML frontmatter")
        return args.contract, _status_from_args(args, None), args.envelope

    metadata = parse_schema_metadata(frontmatter.get("softschema"))
    contract_id = args.contract or (metadata.contract_id if metadata is not None else None)
    if contract_id is None:
        raise UsageError("missing --contract because the document has no softschema.contract")

    return (
        contract_id,
        _status_from_args(args, metadata),
        _envelope_from_args(args, frontmatter, metadata, profile),
    )


def _status_from_args(args: argparse.Namespace, metadata: Any) -> SchemaStatus:
    if args.status is not None:
        return SchemaStatus(args.status)
    if metadata is not None and metadata.status is not None:
        return metadata.status
    return SchemaStatus.soft


def _envelope_from_args(
    args: argparse.Namespace,
    frontmatter: dict[str, Any],
    metadata: Any,
    profile: SchemaProfile = SchemaProfile.frontmatter_md,
) -> str | None:
    # Envelope precedence: --envelope flag > document softschema.envelope > inference.
    if args.envelope is not None:
        return args.envelope
    if metadata is not None and metadata.envelope is not None:
        return metadata.envelope
    if profile == SchemaProfile.pure_yaml:
        return None
    try:
        return infer_envelope_key(frontmatter)
    except EnvelopeAmbiguityError as exc:
        raise UsageError(
            "multiple top-level frontmatter keys; pass --envelope to designate the "
            f"softschema payload (candidates: {', '.join(exc.candidates)})"
        ) from exc


def _compile_cmd(args: argparse.Namespace) -> int:
    # Model-load and compile errors (UsageError, OSError, ...) propagate to the shared
    # `_run_cmd` boundary, which reports them as `softschema compile: ...` and exits 2.
    if args.contract is None:
        raise UsageError("compilation requires --contract")
    validate_contract_id(args.contract)
    if args.schema_id is not None:
        validate_schema_id(args.schema_id)
    model = _load_model(args.model)
    result = compile_model(
        model,
        args.out,
        contract_id=args.contract,
        schema_id=args.schema_id,
        check_only=args.check,
    )
    print(_json(result))
    return 1 if result.drift else 0


def _inspect_cmd(args: argparse.Namespace) -> int:
    _content, frontmatter = read_frontmatter(args.path)
    metadata = None
    envelope_keys: list[str] = []
    if isinstance(frontmatter, dict):
        metadata = parse_schema_metadata(frontmatter.get("softschema"))
        envelope_keys = [str(key) for key in frontmatter if key != "softschema"]
    print(
        _json(
            {
                "path": args.path,
                "has_frontmatter": frontmatter is not None,
                "metadata": metadata,
                "envelope_keys": envelope_keys,
            }
        )
    )
    return 0


def _docs_cmd(args: argparse.Namespace) -> int:
    if args.list_topics or args.topic is None:
        if args.json:
            print(_json(_docs_listing_payload()))
            return 0
        _write_text(_docs_listing())
        return 0
    if args.json:
        topic = DOC_TOPICS[args.topic]
        print(
            _json(
                {
                    "name": args.topic,
                    "title": topic.title,
                    "path": topic.path,
                    "summary": topic.summary,
                    "content": _read_resource(topic.path),
                }
            )
        )
        return 0
    _write_text(_read_resource(DOC_TOPICS[args.topic].path))
    return 0


def _prime_text() -> str:
    """Full agent context: the skill operating rules plus the bundled docs index.

    Byte-identical to the TypeScript ``prime`` command (same SKILL.md, same listing).
    """
    skill = _read_resource("skills/softschema/SKILL.md")
    return f"{skill.rstrip()}\n\n{_docs_listing()}"


def _prime_cmd(args: argparse.Namespace) -> int:
    _write_text(_prime_text())
    return 0


def _generate_cmd(args: argparse.Namespace) -> int:
    any_drift = False
    summary: list[dict[str, Any]] = []
    for path in args.paths:
        try:
            result = regenerate(path, check=args.check)
        except (OSError, ValueError) as exc:
            print(f"softschema generate: {path}: {exc}", file=sys.stderr)
            return 2
        any_drift = any_drift or result.drift
        summary.append(
            {
                "path": str(path),
                "sections": result.sections,
                "drift": result.drift,
                "drift_details": result.drift_details,
            }
        )
    _write_text(_json({"check": args.check, "drift": any_drift, "files": summary}))
    if args.check and any_drift:
        return 1
    return 0


def _doctor_cmd(args: argparse.Namespace) -> int:
    report = _doctor_report()
    if args.json:
        _write_text(_json(report))
    else:
        _write_text(_doctor_text(report))
    return 0


def _doctor_report() -> dict[str, Any]:
    release = _release_metadata()
    return {
        "protocol_version": release["discovery_protocol"],
        "package": {
            "name": "softschema",
            "version": release["logical_version"],
            "release_state": release["release_state"],
        },
        "runtime": {
            "name": "python",
            "version": platform.python_version(),
        },
        "capabilities": {
            "operations": list(DOCTOR_OPERATIONS),
            "artifact_formats": sorted(release["artifact_formats"]["supported"]),
            "model_loaders": ["json-schema", "pydantic"],
            "output_formats": list(DOCTOR_OUTPUT_FORMATS),
            "conformance": release["conformance"],
        },
        "build": _build_metadata(),
    }


def _doctor_text(report: dict[str, Any]) -> str:
    package = report["package"]
    runtime = report["runtime"]
    capabilities = report["capabilities"]
    conformance = capabilities["conformance"]
    lines = [
        f"softschema discovery protocol: {report['protocol_version']}",
        (f"package: {package['name']} {package['version']} ({package['release_state']})"),
        f"runtime: {runtime['name']} {runtime['version']}",
        f"operations: {', '.join(capabilities['operations'])}",
        f"artifact formats: {', '.join(capabilities['artifact_formats'])}",
        f"model loaders: {', '.join(capabilities['model_loaders'])}",
        f"output formats: {', '.join(capabilities['output_formats'])}",
        f"conformance: {conformance['version']} ({conformance['status']})",
    ]
    if report["build"] is not None:
        lines.append(f"build: {report['build']['build_id']}")
    return "\n".join(lines)


SKILL_INSTALL_TARGETS: tuple[Path, ...] = (
    Path(".agents/skills/softschema/SKILL.md"),
    Path(".claude/skills/softschema/SKILL.md"),
)

# The format=fNN stamp lets a future installer recognize this managed surface and
# refuse to clobber a newer format. The package version is intentionally omitted so the
# committed mirrors stay deterministic across dev builds (the drift test renders with the
# locally installed version).
SKILL_DO_NOT_EDIT_MARKER = (
    "<!-- DO NOT EDIT format=f01: written by `softschema skill --install`.\n"
    "Re-run that command to update.\n"
    "-->\n"
)


def _installed_version() -> str:
    try:
        return _pkg_version("softschema")
    except PackageNotFoundError:
        return "unknown"


def _release_metadata() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_read_resource("release-metadata.json")))


def _build_metadata() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_read_resource("build-metadata.json")))


def _agent_help_epilog() -> str:
    release = _release_metadata()
    python_pin = release["packages"]["python"]["pin"]
    npm_pin = release["packages"]["npm"]["pin"]
    return f"""IMPORTANT for agents:
  To set up softschema for this repo as a skill, run one exact-pinned command from the repo root:
    uvx --from 'softschema=={python_pin}' softschema skill --install
    # or
    npx --yes softschema@{npm_pin} skill --install
    # or
    bunx --bun softschema@{npm_pin} skill --install
  Then run `softschema doctor --json`, and read `softschema skill --brief` and
  `softschema docs --list` for capabilities, operating rules, and bundled docs."""


def _rendered_skill_text() -> str:
    return _read_resource(DOC_TOPICS["skill"].path)


def _skill_cmd(args: argparse.Namespace) -> int:
    if args.install:
        request = InstallRequest(
            project=args.project,
            global_scope=args.global_scope,
            directory=args.dir,
            agents=tuple(args.agent),
            all_agents=args.all_agents,
            no_repo_check=args.no_repo_check,
            dry_run=args.dry_run,
        )
        exit_code, report = execute_skill_install(
            request,
            rendered_skill=_rendered_skill_text(),
            marker=SKILL_DO_NOT_EDIT_MARKER,
            package_version=_installed_version(),
            cwd=Path.cwd(),
        )
        _write_text(format_install_plan_text(report) if args.text else _json(report))
        return exit_code
    installer_option = (
        args.project
        or args.global_scope
        or args.dir is not None
        or args.agent
        or args.all_agents
        or args.no_repo_check
        or args.dry_run
        or args.json
        or args.text
    )
    if installer_option:
        raise SkillInstallUsageError("installer options require --install")
    if args.brief:
        _write_text(_brief_skill_text())
        return 0
    _write_text(_rendered_skill_text())
    return 0


def _load_model(spec: str) -> type[BaseModel]:
    module_name, _, attr = spec.partition(":")
    if not module_name or not attr:
        raise UsageError(f"model spec must be module:Class, got {spec!r}")
    # Make the invoking directory importable so example modules outside the package
    # (e.g. examples.movie_page.model) resolve when running the CLI from a checkout.
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    module = importlib.import_module(module_name)
    obj = getattr(module, attr, None)
    if obj is None:
        raise UsageError(f"{spec!r} has no attribute {attr!r}")
    if not isinstance(obj, type) or not issubclass(obj, BaseModel):
        raise UsageError(f"{spec!r} is not a Pydantic BaseModel class")
    return obj


def _docs_listing() -> str:
    lines = [
        "Available softschema docs:",
        "",
    ]
    width = max(len(name) for name in DOC_TOPICS)
    for name, topic in sorted(DOC_TOPICS.items()):
        lines.append(f"  {name.ljust(width)}  {topic.summary}")
    lines.extend(
        [
            "",
            "Run `softschema docs <topic>` to print a document.",
            "Copy examples from the printed docs or from the repository files; "
            "the CLI does not scaffold or mutate projects.",
        ]
    )
    return "\n".join(lines)


def _docs_listing_payload() -> dict[str, Any]:
    return {
        "topics": [
            {
                "name": name,
                "title": topic.title,
                "path": topic.path,
                "summary": topic.summary,
            }
            for name, topic in sorted(DOC_TOPICS.items())
        ],
        "copyable_examples": [
            "example",
            "example-artifact",
            "example-model",
            "example-host",
            "example-schema",
        ],
        "scaffolding": False,
    }


def _brief_skill_text() -> str:
    return (
        f"# softschema Skill Brief\n\n{_extract_marked_section(_rendered_skill_text()).strip()}\n"
    )


def _extract_marked_section(text: str) -> str:
    start = text.find(BRIEF_MARKER_START)
    end = text.find(BRIEF_MARKER_END)
    if start == -1 or end == -1 or end <= start:
        raise ValueError("skills/softschema/SKILL.md is missing the brief marker block")
    return text[start + len(BRIEF_MARKER_START) : end]


def _read_resource(relative_path: str) -> str:
    dev_path = _dev_resource_path(relative_path)
    if dev_path is not None:
        return dev_path.read_text(encoding="utf-8")

    resource_path = resources.files("softschema").joinpath("resources", *Path(relative_path).parts)
    try:
        return resource_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"bundled softschema resource not found: {relative_path}") from None


_SOURCE_CLI_RELATIVE_PATH = Path("packages/python/src/softschema/cli.py")
_SOURCE_CHECKOUT_MARKERS: tuple[Path, ...] = (
    Path("pyproject.toml"),
    Path("packages/typescript/src/cli.ts"),
    Path("skills/softschema/SKILL.md"),
)


def _source_checkout_root(module_path: Path) -> Path | None:
    """Return the repo root only when ``module_path`` has the exact source-tree identity."""
    resolved_module = module_path.resolve()
    source_depth = len(_SOURCE_CLI_RELATIVE_PATH.parts) - 1
    if len(resolved_module.parents) <= source_depth:
        return None
    root = resolved_module.parents[source_depth]
    if (root / _SOURCE_CLI_RELATIVE_PATH).resolve() != resolved_module:
        return None
    if not all((root / marker).is_file() for marker in _SOURCE_CHECKOUT_MARKERS):
        return None
    return root


def _dev_resource_path(relative_path: str) -> Path | None:
    """Resolve a live source resource only from this repository's exact checkout layout."""
    root = _source_checkout_root(Path(__file__))
    if root is None:
        return None
    candidate = root / relative_path
    return candidate if candidate.is_file() else None


def _write_text(text: str) -> None:
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")


def _json(value: Any) -> str:
    # ensure_ascii=False keeps non-ASCII literal so output matches the TypeScript
    # CLI's JSON.stringify (which never escapes) byte-for-byte in golden tests.
    return json.dumps(_plain(value), indent=2, sort_keys=True, ensure_ascii=False)


def _plain(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, BaseModel):
        return _plain(value.model_dump(by_alias=True))
    if is_dataclass(value) and not isinstance(value, type):
        return _plain(asdict(cast(Any, value)))
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    if isinstance(value, type):
        return f"{value.__module__}:{value.__name__}"
    # Canonical number form (whole-valued floats without a trailing `.0`) so the
    # echoed `values` block matches the TypeScript CLI byte-for-byte; see errors.py.
    return canonical_number(value)


if __name__ == "__main__":
    sys.exit(main())
