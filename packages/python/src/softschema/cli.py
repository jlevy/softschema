"""Command-line interface for softschema."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from importlib import resources
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any, cast

from frontmatter_format import fmf_read
from pydantic import BaseModel, ValidationError

from softschema.compile import compile_model
from softschema.generate import regenerate
from softschema.models import Contract, SchemaStatus, parse_schema_metadata
from softschema.validate import validate_artifact


@dataclass(frozen=True)
class ResourceTopic:
    title: str
    path: str
    summary: str


DOC_TOPICS: dict[str, ResourceTopic] = {
    "readme": ResourceTopic("README", "README.md", "Short first-visitor overview."),
    "guide": ResourceTopic(
        "Softschema Guide",
        "docs/softschema-guide.md",
        "Concepts, mental model, and adoption path.",
    ),
    "spec": ResourceTopic(
        "Softschema Spec",
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
        "Installing uv and Python.",
    ),
    "publishing": ResourceTopic(
        "Publishing",
        "docs/publishing.md",
        "Release and PyPI workflow.",
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
    "skill": ResourceTopic(
        "Softschema Skill",
        "skills/softschema/SKILL.md",
        "Portable agent skill instructions.",
    ),
    "agents": ResourceTopic(
        "Agent Instructions",
        "AGENTS.md",
        "Repo-level agent instructions.",
    ),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="softschema",
        description="Validate and explain soft schema Markdown/YAML artifacts.",
        epilog=(
            "IMPORTANT for agents: run `softschema skill --brief` for operating "
            "rules, then `softschema docs --list` to discover bundled docs "
            "(`guide`, `spec`, and `example-artifact` are the key ones)."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate an artifact.")
    validate_parser.add_argument("path", type=Path)
    validate_parser.add_argument("--contract", help="Override the document contract ID.")
    validate_parser.add_argument("--envelope", help="Override the inferred envelope key.")
    validate_parser.add_argument(
        "--model",
        help="Pydantic model as module:Class. Required unless --schema is provided.",
    )
    validate_parser.add_argument(
        "--schema",
        type=Path,
        help="JSON Schema YAML sidecar. Required unless --model is provided.",
    )
    validate_parser.add_argument(
        "--status",
        choices=[status.value for status in SchemaStatus],
        help="Override the document status.",
    )
    validate_parser.set_defaults(func=_validate_cmd)

    compile_parser = subparsers.add_parser("compile", help="Compile a Pydantic model.")
    compile_parser.add_argument("model", help="Pydantic model as module:Class.")
    compile_parser.add_argument("--out", required=True, type=Path)
    compile_parser.add_argument("--contract")
    compile_parser.add_argument("--check", action="store_true")
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
    return args.func(args)


def _validate_cmd(args: argparse.Namespace) -> int:
    try:
        if args.model is None and args.schema is None:
            raise ValueError("missing validation implementation; pass --model, --schema, or both")
        contract_id, status, envelope_key = _infer_validation_binding(args)
        model = _load_model(args.model) if args.model else None
    except (TypeError, ValueError, ValidationError) as exc:
        print(f"softschema validate: {exc}", file=sys.stderr)
        return 2
    contract = Contract(
        id=contract_id,
        model=model,
        envelope_key=envelope_key,
        schema_path=args.schema,
        status=status,
    )
    result = validate_artifact(args.path, contract=contract)
    print(_json(result))
    return 0 if result.ok else 1


def _infer_validation_binding(args: argparse.Namespace) -> tuple[str, SchemaStatus, str | None]:
    _content, frontmatter = fmf_read(args.path)
    if not isinstance(frontmatter, dict):
        if args.contract is None:
            raise ValueError("missing --contract because the document has no YAML frontmatter")
        return args.contract, _status_from_args(args, None), args.envelope

    metadata = parse_schema_metadata(frontmatter.get("softschema"))
    contract_id = args.contract or (metadata.contract_id if metadata is not None else None)
    if contract_id is None:
        raise ValueError("missing --contract because the document has no softschema.contract")

    return contract_id, _status_from_args(args, metadata), _envelope_from_args(args, frontmatter)


def _status_from_args(args: argparse.Namespace, metadata: Any) -> SchemaStatus:
    if args.status is not None:
        return SchemaStatus(args.status)
    if metadata is not None and metadata.status is not None:
        return metadata.status
    return SchemaStatus.soft


def _envelope_from_args(args: argparse.Namespace, frontmatter: dict[str, Any]) -> str | None:
    if args.envelope is not None:
        return args.envelope
    envelope_keys = [str(key) for key in frontmatter if key != "softschema"]
    if len(envelope_keys) == 1:
        return envelope_keys[0]
    if not envelope_keys:
        return None
    raise ValueError(
        "multiple top-level frontmatter keys; pass --envelope to designate the "
        f"softschema payload (candidates: {', '.join(envelope_keys)})"
    )


def _compile_cmd(args: argparse.Namespace) -> int:
    try:
        model = _load_model(args.model)
    except (TypeError, ValueError) as exc:
        print(f"softschema compile: {exc}", file=sys.stderr)
        return 2
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


def _generate_cmd(args: argparse.Namespace) -> int:
    any_drift = False
    summary: list[dict[str, Any]] = []
    for path in args.paths:
        try:
            result = regenerate(path, check=args.check)
        except (OSError, ValueError) as exc:
            print(f"error: {path}: {exc}", file=sys.stderr)
            return 1
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


SKILL_INSTALL_TARGETS: tuple[Path, ...] = (
    Path(".agents/skills/softschema/SKILL.md"),
    Path(".claude/skills/softschema/SKILL.md"),
)

SKILL_DO_NOT_EDIT_MARKER = (
    "<!-- DO NOT EDIT: written by `softschema skill --install`.\n"
    "Re-run that command to update.\n"
    "-->\n"
)


def _installed_version() -> str:
    try:
        return _pkg_version("softschema")
    except PackageNotFoundError:
        return "unknown"


def _rendered_skill_text() -> str:
    raw = _read_resource(DOC_TOPICS["skill"].path)
    return raw.replace("<version>", _installed_version())


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


def _install_skill(base_dir: Path) -> dict[str, Any]:
    payload = _install_skill_payload(_rendered_skill_text())
    files: list[dict[str, str]] = []
    for relative in SKILL_INSTALL_TARGETS:
        target = base_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = target.read_text(encoding="utf-8") if target.exists() else None
        if existing == payload:
            status = "unchanged"
        else:
            target.write_text(payload, encoding="utf-8")
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
        raise ValueError(f"model spec must be module:Class, got {spec!r}")
    # Make the invoking directory importable so example modules outside the package
    # (e.g. examples.movie_page.model) resolve when running the CLI from a checkout.
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    module = importlib.import_module(module_name)
    obj = getattr(module, attr, None)
    if obj is None:
        raise ValueError(f"{spec!r} has no attribute {attr!r}")
    if not isinstance(obj, type) or not issubclass(obj, BaseModel):
        raise TypeError(f"{spec!r} is not a Pydantic BaseModel class")
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
        "copyable_examples": ["example", "example-artifact", "example-model", "example-host"],
        "scaffolding": False,
    }


def _brief_skill_text() -> str:
    return """# Softschema Skill Brief

Use soft schemas when humans or agents write Markdown/YAML artifacts and tools need to
consume some values reliably.

- Read `softschema docs guide` for the mental model.
- Read `softschema docs spec` for the exact artifact format.
- Inspect `softschema docs example` and `softschema docs example-artifact` for the
  copyable movie example.
- Treat YAML/frontmatter as authoritative.
- Do not parse Markdown body prose or tables for consumed values.
- Use `softschema.contract` to name the payload contract.
- Keep examples copyable; do not scaffold or mutate a target project unless the user
  explicitly asks for that workflow.
"""


def _read_resource(relative_path: str) -> str:
    resource_path = resources.files("softschema").joinpath("resources", *Path(relative_path).parts)
    try:
        return resource_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        pass

    dev_path = _dev_repo_root() / relative_path
    if dev_path.is_file():
        return dev_path.read_text(encoding="utf-8")

    raise FileNotFoundError(f"bundled softschema resource not found: {relative_path}")


def _dev_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "docs").is_dir():
            return parent
    return Path(__file__).resolve().parents[4]


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
