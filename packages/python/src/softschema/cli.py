"""Command-line interface for softschema."""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import sys
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from importlib import resources
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any, cast

from frontmatter_format import FmFormatError, fmf_read
from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAMLError
from strif import atomic_write_text

from softschema.compile import compile_model
from softschema.generate import regenerate
from softschema.models import Contract, SchemaStatus, parse_schema_metadata
from softschema.validate import EnvelopeAmbiguityError, infer_envelope_key, validate_artifact

BRIEF_MARKER_START = "<!-- BEGIN SOFTSCHEMA BRIEF -->"
BRIEF_MARKER_END = "<!-- END SOFTSCHEMA BRIEF -->"
RUNNER_COMMANDS: tuple[str, ...] = ("softschema", "uvx", "npx")
RUNNER_INVOCATIONS: dict[str, str] = {
    "softschema": "softschema",
    "uvx": "uvx softschema@latest",
    "npx": "npx softschema@latest",
}

AGENT_HELP_EPILOG = """IMPORTANT for agents:
  To set up softschema for this repo as a skill, run one command from the repo root:
    uvx softschema@latest skill --install
    # or
    npx softschema@latest skill --install
  Then read `softschema skill --brief` and `softschema docs --list` for operating rules
  and bundled docs."""


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
        epilog=AGENT_HELP_EPILOG,
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
    compile_parser.add_argument("--contract", help="Contract ID stamped into the compiled schema.")
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
        help="Report softschema version and runner availability.",
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
        help=(
            "Write the skill into .agents/skills/softschema/SKILL.md and "
            ".claude/skills/softschema/SKILL.md (relative to the current directory)."
        ),
    )
    skill_parser.set_defaults(func=_skill_cmd)

    args = parser.parse_args(argv)
    return _run_cmd(args.command, args.func, args)


def _validate_cmd(args: argparse.Namespace) -> int:
    # Without --model/--schema this is a metadata-only check: frontmatter parses,
    # the softschema: block is well-formed, and the envelope resolves; structural
    # and semantic layers are reported as skipped. Useful from the `soft` stage on.
    # Read the document once here; both binding inference and validate_artifact
    # reuse this frontmatter, so the file is parsed a single time.
    _content, frontmatter = fmf_read(args.path)
    contract_id, status, envelope_key = _infer_validation_binding(args, frontmatter)
    model = _load_model(args.model) if args.model else None
    contract = Contract(
        id=contract_id,
        model=model,
        envelope_key=envelope_key,
        schema_path=args.schema,
        status=status,
    )
    result = validate_artifact(args.path, contract=contract, frontmatter=frontmatter)
    print(_json(result))
    return 0 if result.ok else 1


def _infer_validation_binding(
    args: argparse.Namespace, frontmatter: Any
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
        _envelope_from_args(args, frontmatter, metadata),
    )


def _status_from_args(args: argparse.Namespace, metadata: Any) -> SchemaStatus:
    if args.status is not None:
        return SchemaStatus(args.status)
    if metadata is not None and metadata.status is not None:
        return metadata.status
    return SchemaStatus.soft


def _envelope_from_args(
    args: argparse.Namespace, frontmatter: dict[str, Any], metadata: Any
) -> str | None:
    # Envelope precedence: --envelope flag > document softschema.envelope > inference.
    if args.envelope is not None:
        return args.envelope
    if metadata is not None and metadata.envelope is not None:
        return metadata.envelope
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
    model = _load_model(args.model)
    result = compile_model(model, args.out, contract_id=args.contract, check_only=args.check)
    print(_json(result))
    return 1 if result.drift else 0


def _inspect_cmd(args: argparse.Namespace) -> int:
    _content, frontmatter = fmf_read(args.path)
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
    runners = []
    for name in RUNNER_COMMANDS:
        path = _find_runner(name)
        runners.append({"name": name, "available": path is not None, "path": path})
    recommended = next(
        (RUNNER_INVOCATIONS[runner["name"]] for runner in runners if runner["available"]),
        None,
    )
    return {
        "version": _installed_version(),
        "runners": runners,
        "recommended_invocation": recommended,
    }


def _doctor_text(report: dict[str, Any]) -> str:
    lines = [
        f"softschema version: {report['version']}",
        "available runners:",
    ]
    for runner in report["runners"]:
        status = "yes" if runner["available"] else "no"
        path = f" ({runner['path']})" if runner["path"] else ""
        lines.append(f"  {runner['name']}: {status}{path}")
    recommended = report["recommended_invocation"] or "unavailable"
    lines.append(f"recommended invocation: {recommended}")
    if report["recommended_invocation"] is None:
        lines.append("Install uv or Node, then retry.")
    return "\n".join(lines)


def _find_runner(name: str) -> str | None:
    return shutil.which(name)


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


def _rendered_skill_text() -> str:
    return _read_resource(DOC_TOPICS["skill"].path)


def _install_skill_payload(rendered: str) -> str:
    """Insert the DO NOT EDIT marker after the closing frontmatter delimiter."""
    lines = rendered.split("\n")
    delimiter_count = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            delimiter_count += 1
            if delimiter_count == 2:
                lines.insert(i + 1, SKILL_DO_NOT_EDIT_MARKER)
                break
    return "\n".join(lines)


def _resolve_install_base(start: Path) -> Path:
    """The nearest ancestor containing ``.git`` (so installs land at the repo root),
    falling back to ``start`` when none is found."""
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start


def _install_skill(base_dir: Path) -> dict[str, Any]:
    base_dir = _resolve_install_base(base_dir)
    payload = _install_skill_payload(_rendered_skill_text())
    files: list[dict[str, str]] = []
    for relative in SKILL_INSTALL_TARGETS:
        target = base_dir / relative
        existing = target.read_text(encoding="utf-8") if target.exists() else None
        if existing == payload:
            status = "unchanged"
        else:
            atomic_write_text(target, payload, make_parents=True)
            status = "updated" if existing is not None else "created"
        files.append({"path": str(relative), "status": status})
    return {
        "version": _installed_version(),
        "base_dir": str(base_dir),
        "files": files,
    }


def _skill_cmd(args: argparse.Namespace) -> int:
    if args.install:
        _write_text(_json(_install_skill(Path.cwd())))
        return 0
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


def _dev_resource_path(relative_path: str) -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "docs").is_dir():
            candidate = parent / relative_path
            return candidate if candidate.is_file() else None
    return None


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
    return value


if __name__ == "__main__":
    sys.exit(main())
