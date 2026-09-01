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

from pydantic import BaseModel, ValidationError
from strif import atomic_write_text

from softschema._portable import PortableInputError, opens_frontmatter_fence, read_utf8
from softschema.compile import compile_model
from softschema.errors import canonical_number
from softschema.generate import regenerate
from softschema.models import Contract, SchemaProfile, SchemaStatus, parse_schema_metadata
from softschema.pipeline import repair_and_validate_artifact
from softschema.repair import RepairResult, repair_artifact
from softschema.validate import (
    EnvelopeAmbiguityError,
    infer_envelope_key,
    parse_frontmatter_text,
    parse_yaml_text,
    read_frontmatter_doc,
    read_yaml_doc,
    unreadable_artifact_result,
    validate_artifact,
)

BRIEF_MARKER_START = "<!-- BEGIN SOFTSCHEMA BRIEF -->"
BRIEF_MARKER_END = "<!-- END SOFTSCHEMA BRIEF -->"
ZERO_INSTALL_PACKAGE = "softschema@latest"
RUNNER_COMMANDS: tuple[str, ...] = ("softschema", "uvx", "npx")
RUNNER_INVOCATIONS: dict[str, str] = {
    "softschema": "softschema",
    "uvx": f"uvx {ZERO_INSTALL_PACKAGE}",
    "npx": f"npx -y {ZERO_INSTALL_PACKAGE}",
}

AGENT_HELP_EPILOG = f"""IMPORTANT for agents:
  To set up softschema for this repo as a skill, run one command from the repo root:
    uvx {ZERO_INSTALL_PACKAGE} skill --install --scope project --agent portable --agent claude
    # or
    npx -y {ZERO_INSTALL_PACKAGE} skill --install --scope project --agent portable --agent claude
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
        version=f"%(prog)s {_installed_version()} (Python)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help=(
            "Validate an artifact, read-only. A self-describing artifact "
            "(softschema.contract, schema, envelope) needs no flags; flags override the "
            "document. Never writes; to fix an artifact, use `repair`."
        ),
    )
    _add_binding_args(validate_parser)
    validate_parser.set_defaults(func=_validate_cmd)

    repair_parser = subparsers.add_parser(
        "repair",
        help=(
            "Repair unparsable YAML and conform scalars to the declared types, write the "
            "file, then validate. Reports every change under `repairs`."
        ),
    )
    _add_binding_args(repair_parser)
    # `--dry-run` and `--check` both suppress the write and differ in what they assert, the
    # same way they differ elsewhere in this CLI: `skill --install --dry-run` previews and
    # exits 0, `generate --check` previews and exits 1 on drift. A caller asking "what
    # would this do?" wants the first; a gate asserting "nothing needs doing" wants the
    # second.
    #
    # Their exclusion is checked in `_repair_cmd`, not with argparse's mutually exclusive
    # group. The group's message is argparse's own — a usage block plus "argument --check:
    # not allowed with argument --dry-run" — which Commander cannot reproduce, and the two
    # CLIs must word softschema's own diagnostics identically. The golden corpus asserts
    # this line exactly for that reason.
    repair_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write; report what would change. Exit 1 only if the result is invalid.",
    )
    repair_parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if anything would change.",
    )
    repair_parser.set_defaults(func=_repair_cmd)

    compile_parser = subparsers.add_parser("compile", help="Compile a Pydantic model.")
    compile_parser.add_argument("model", help="Pydantic model as module:Class.")
    compile_parser.add_argument(
        "--out", required=True, type=Path, help="Output path for the compiled schema."
    )
    compile_parser.add_argument(
        "--contract", required=True, help="Logical contract ID stored in x-softschema."
    )
    compile_parser.add_argument("--schema-id", help="Optional absolute JSON Schema resource URI.")
    compile_parser.add_argument(
        "--check", action="store_true", help="Do not write; exit 1 on drift."
    )
    compile_parser.set_defaults(func=_compile_cmd)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect artifact metadata.")
    inspect_parser.add_argument("path", type=Path)
    inspect_parser.add_argument(
        "--profile",
        choices=[profile.value for profile in SchemaProfile],
        help="Override the artifact profile; detected from the document when omitted.",
    )
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
    skill_parser.add_argument("--scope", choices=("project", "personal"))
    skill_parser.add_argument(
        "--agent", action="append", choices=("portable", "claude"), dest="agents"
    )
    skill_parser.add_argument("--dry-run", action="store_true", help="Preview without writing.")
    skill_parser.add_argument(
        "--install",
        action="store_true",
        help="Install the skill for each selected --agent at the selected --scope.",
    )
    skill_parser.set_defaults(func=_skill_cmd)

    args = parser.parse_args(argv)
    return _run_cmd(args.command, args.func, args)


# Extensions that settle the profile on the file name alone. Checked before the
# frontmatter fence, because a YAML document may legitimately open with the `---`
# document-start marker that would otherwise scan as the start of a fence.
_YAML_SUFFIXES = frozenset({".yaml", ".yml"})


@dataclass(frozen=True)
class _ArtifactRead:
    """A document read once, together with the profile it was read under."""

    profile: SchemaProfile
    document: Any


def _read_artifact(path: Path, profile: SchemaProfile | None) -> _ArtifactRead:
    """Read an artifact under a declared profile, or detect its profile and read it.

    Detection, when no profile is declared:

    1. A `*.yaml`/`*.yml` file is pure-yaml on its name alone.
    2. A document with a frontmatter fence is frontmatter-md.
    3. A fenceless document whose whole text parses to a mapping carrying a
       `softschema:` block is pure-yaml. That block is the spec's metadata block, so
       finding it at the root of a fenceless document is what separates a pure-yaml
       artifact from prose that happens to parse as YAML.
    4. Anything else stays frontmatter-md and reports the same `no_frontmatter` it did
       before detection existed.

    Case 3 reads the file a second time rather than re-implementing the fence scan
    here; it applies only to a fenceless document that is not named `*.yaml`, which
    without detection could not validate at all.
    """
    if profile is SchemaProfile.pure_yaml:
        return _ArtifactRead(profile, read_yaml_doc(path))
    if profile is SchemaProfile.frontmatter_md:
        _content, frontmatter = read_frontmatter_doc(path)
        return _ArtifactRead(profile, frontmatter)
    if path.suffix.lower() in _YAML_SUFFIXES:
        return _ArtifactRead(SchemaProfile.pure_yaml, read_yaml_doc(path))
    _content, frontmatter = read_frontmatter_doc(path)
    if frontmatter is not None:
        return _ArtifactRead(SchemaProfile.frontmatter_md, frontmatter)
    root = _yaml_root_or_none(path)
    if isinstance(root, dict) and "softschema" in root:
        return _ArtifactRead(SchemaProfile.pure_yaml, root)
    return _ArtifactRead(SchemaProfile.frontmatter_md, None)


def _yaml_root_or_none(path: Path) -> Any:
    """Parse a fenceless document as YAML, or return ``None`` when it is not YAML.

    Only used to spot a pure-yaml artifact that is not named `*.yaml`. A failure here
    means "not a pure-yaml artifact", not an error to report: the document stays
    frontmatter-md and validation emits its own diagnostic for it.
    """
    try:
        return read_yaml_doc(path)
    except (OSError, PortableInputError):
        return None


def _add_binding_args(parser: argparse.ArgumentParser) -> None:
    """The artifact and contract-binding flags shared by `validate` and `repair`.

    Both commands answer a question about one artifact under one contract, and the
    binding is resolved the same way for each. Defining the flags once is what keeps the
    two from drifting into subtly different override precedence.
    """
    parser.add_argument("path", type=Path)
    parser.add_argument("--contract", help="Override the document contract ID.")
    parser.add_argument(
        "--envelope",
        help="Override the envelope key (softschema.envelope or single-key inference).",
    )
    parser.add_argument(
        "--model",
        help=(
            "Pydantic model as module:Class for semantic validation. Optional. "
            "Imports and runs local code; use only with trusted models."
        ),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        help=(
            "Compiled JSON Schema (YAML or JSON). Optional override; without it the "
            "document's softschema.schema binding is used when present."
        ),
    )
    parser.add_argument(
        "--status",
        choices=[status.value for status in SchemaStatus],
        help="Override the document status.",
    )
    parser.add_argument(
        "--profile",
        choices=[profile.value for profile in SchemaProfile],
        help=(
            "Override the artifact profile. Optional; without it a *.yaml/*.yml file, "
            "or a fenceless document whose root carries a softschema: block, is read "
            "as pure-yaml and anything else as frontmatter-md."
        ),
    )


def _validate_cmd(args: argparse.Namespace) -> int:
    # Without --model/--schema this is a metadata-only check: the document parses,
    # the softschema: block is well-formed, and the envelope resolves; structural
    # and semantic layers are reported as skipped. Useful from the `soft` stage on.
    # Read the document once here; both binding inference and validate_artifact
    # reuse that parse, so the file is parsed a single time.
    #
    # The read is unconditional, and that is the point rather than an accident of where
    # the binding comes from. `validate` is the consuming-side gate: an artifact it
    # cannot open is not a failing artifact, it is not an artifact, and it exits 2 with
    # one line. Reading only when binding inference needed the document made that verdict
    # depend on whether `--contract` was passed — the same unreadable file exited 2
    # without the flag and 1 with it. Strictness is a property of this command.
    read = _read_artifact(args.path, _profile_from_args(args))
    contract_id, status, envelope_key = _infer_validation_binding(args, read.document, read.profile)
    model = _load_model(args.model) if args.model else None
    contract = Contract(
        id=contract_id,
        model=model,
        envelope_key=envelope_key,
        schema_path=args.schema,
        status=status,
        profile=read.profile,
    )
    result = validate_artifact(args.path, contract=contract, document=read.document)
    if result.outcome == "input_error":
        raise RuntimeError("pre-parsed CLI validation returned an input error")
    print(_json(result))
    if result.outcome == "valid":
        return 0
    return 1


def _repair_cmd(args: argparse.Namespace) -> int:
    """The `repair` command: repair, conform, validate, and write unless asked not to.

    Repair runs *before* binding inference, not after. The document this command exists to
    rescue is one that does not parse, and the contract, schema, and envelope are all read
    out of that same unparsable frontmatter — inferring the binding first would fail on
    exactly the artifacts the command is for.

    The repair is then handed to the pipeline rather than recomputed, so the file is still
    read once and written at most once.

    Unlike `validate`, an unreadable document is this command's normal input, not a usage
    error. It is reported as a record in the result, whether or not a binding could be
    inferred from it. Raising here would hand the one caller who most needs the diagnostic
    — the agent that just wrote the file — an exit code and nothing else.
    """
    if args.dry_run and args.check:
        raise UsageError("--dry-run and --check are mutually exclusive")
    write = not (args.dry_run or args.check)
    profile = _profile_from_args(args) or _detect_profile(args.path)
    repaired = repair_artifact(args.path, profile=profile, write=False)
    document, parse_error = _parse_after_repair(repaired.text, profile, str(args.path))

    # Repair could not rescue the document and the caller named no contract, so there is
    # no binding to validate under. Report the read failure rather than raising: a
    # contract ID cannot be invented for a document that declares none, and the agent that
    # just wrote this file needs the diagnostic, not an exit code.
    if not isinstance(document, dict) and args.contract is None:
        result = unreadable_artifact_result(
            args.path,
            profile=profile,
            kind=_repair_failure_kind(repaired, parse_error),
            message=_repair_failure_message(repaired, parse_error, args.path, profile),
        )
        print(_json(result))
        return 1

    contract_id, status, envelope_key = _infer_repair_binding(args, document, profile)
    contract = Contract(
        id=contract_id,
        model=_load_model(args.model) if args.model else None,
        envelope_key=envelope_key,
        schema_path=args.schema,
        status=status,
        profile=profile,
    )
    result = repair_and_validate_artifact(
        args.path, contract=contract, write=write, repaired=repaired
    )
    print(_json(result))
    # `--check` answers "would this change?", so a document needing repair fails the check
    # even when it would validate afterward. Same shape as `generate --check`, and it is
    # what lets a gate reject an unrepaired artifact. `--dry-run` asks the other question —
    # "what would this do?" — and keeps the ordinary pass condition.
    if args.check and result.repairs:
        return 1
    return 0 if result.outcome == "valid" else 1


def _repair_failure_kind(repaired: RepairResult, parse_error: PortableInputError | None) -> str:
    """The record kind for a document repair could not make readable.

    Repair's own error code wins when it has one — an alias or a merge key is a precise
    diagnosis, and quoting could never have fixed it. Otherwise the reader's code names
    the failure, which is the ordinary case: repair reports success for a document with no
    frontmatter region to rewrite, leaving the reader to say why it cannot be opened.
    """
    if repaired.error_code:
        return repaired.error_code
    return parse_error.code if parse_error is not None else "yaml_parse_error"


def _repair_failure_message(
    repaired: RepairResult,
    parse_error: PortableInputError | None,
    path: Path,
    profile: SchemaProfile,
) -> str:
    if repaired.error_message:
        return repaired.error_message
    if parse_error is not None:
        return str(parse_error)
    if profile is SchemaProfile.pure_yaml:
        return f"the document root is not a YAML mapping: `{path}`"
    return f"the document has no YAML frontmatter: `{path}`"


def _detect_profile(path: Path) -> SchemaProfile:
    """Detect an artifact's profile without requiring it to parse.

    The ordinary detection in `_read_artifact` parses the document, which an artifact
    awaiting repair does not do. Every rule that does not need a successful parse is kept:
    the filename, then the presence of a frontmatter fence. A fenceless document that will
    not parse falls back to frontmatter-md and reports `no_frontmatter`, exactly as it does
    without `--repair`.

    The fence test asks whether the document *opens* a fence, not whether it can be
    split. A document that opens a fence and never closes it is frontmatter-md and the
    reader rejects it; treating it as fenceless would route it to the pure-yaml rule
    below, where its leading `---` reads as a YAML document-start marker and the whole
    file parses cleanly. That is how `--repair` once called an artifact valid that plain
    `validate` could not read at all.
    """
    if path.suffix.lower() in _YAML_SUFFIXES:
        return SchemaProfile.pure_yaml
    try:
        text = read_utf8(path)
    except (OSError, PortableInputError):
        return SchemaProfile.frontmatter_md
    if opens_frontmatter_fence(text.replace("\r\n", "\n")):
        return SchemaProfile.frontmatter_md
    root = _yaml_root_or_none(path)
    if isinstance(root, dict) and "softschema" in root:
        return SchemaProfile.pure_yaml
    return SchemaProfile.frontmatter_md


def _parse_after_repair(
    text: str | None, profile: SchemaProfile, source: str = "<text>"
) -> tuple[Any, PortableInputError | None]:
    """Parse the repaired text for binding inference, tolerating one that still fails.

    Returns the parsed document and, when repair could not rescue it, the error that
    stopped it. The error has to travel with the ``None``, because it is what names the
    cause in the record `repair` reports — "the document could not be read" is not a
    diagnostic, and repair itself does not produce one here: an unterminated fence leaves
    no frontmatter region to rewrite, which `repair_artifact` correctly treats as
    validation's verdict rather than a repair failure.

    ``source`` only names the document in that message.
    """
    if text is None:
        return None, None
    try:
        if profile is SchemaProfile.pure_yaml:
            return parse_yaml_text(text), None
        _body, frontmatter = parse_frontmatter_text(text, source=source)
    except PortableInputError as exc:
        return None, exc
    return frontmatter, None


def _profile_from_args(args: argparse.Namespace) -> SchemaProfile | None:
    profile = getattr(args, "profile", None)
    return SchemaProfile(profile) if profile is not None else None


def _infer_validation_binding(
    args: argparse.Namespace,
    document: Any,
    profile: SchemaProfile,
) -> tuple[str, SchemaStatus, str | None]:
    """Resolve the contract binding for `validate`, which requires one.

    Reached only for a document that read cleanly — `validate` refuses an unreadable one
    before this — so a missing binding here really is a missing binding, and naming it as
    a usage error is honest.
    """
    if not isinstance(document, dict):
        if args.contract is None:
            raise UsageError(_missing_contract_reason(profile))
        return args.contract, _status_from_args(args, None), args.envelope

    metadata = parse_schema_metadata(document.get("softschema"))
    contract_id = args.contract or (metadata.contract_id if metadata is not None else None)
    if contract_id is None:
        raise UsageError("missing --contract because the document has no softschema.contract")

    return (
        contract_id,
        _status_from_args(args, metadata),
        _envelope_from_args(args, document, metadata, profile),
    )


def _infer_repair_binding(
    args: argparse.Namespace, document: Any, profile: SchemaProfile
) -> tuple[str, SchemaStatus, str | None]:
    """Resolve the contract binding for `repair`, which tolerates not finding one.

    An unreadable document is this command's normal input, so a missing binding is not a
    usage error here — it is a consequence of the failure validation is about to report.
    The contract ID goes out empty in that case, which is what the artifact actually
    declares: nothing legible.

    Raising instead is how this path once told an agent to pass `--contract` for a
    document that could not be opened, advising a flag that would not have helped.
    """
    if not isinstance(document, dict):
        return args.contract or "", _status_from_args(args, None), args.envelope
    return _infer_validation_binding(args, document, profile)


def _missing_contract_reason(profile: SchemaProfile) -> str:
    if profile is SchemaProfile.pure_yaml:
        return "missing --contract because the document root is not a YAML mapping"
    return "missing --contract because the document has no YAML frontmatter"


def _status_from_args(args: argparse.Namespace, metadata: Any) -> SchemaStatus:
    if args.status is not None:
        return SchemaStatus(args.status)
    if metadata is not None and metadata.status is not None:
        return metadata.status
    return SchemaStatus.soft


def _envelope_from_args(
    args: argparse.Namespace,
    document: dict[str, Any],
    metadata: Any,
    profile: SchemaProfile,
) -> str | None:
    # Envelope precedence: --envelope flag > document softschema.envelope > inference.
    if args.envelope is not None:
        return args.envelope
    if metadata is not None and metadata.envelope is not None:
        return metadata.envelope
    if profile is SchemaProfile.pure_yaml:
        # The spec exempts pure-yaml from single-key inference and multi-key ambiguity
        # rejection: with nothing designated, the whole root minus the metadata block
        # is the payload, which is what an undesignated envelope key means downstream.
        return None
    try:
        return infer_envelope_key(document)
    except EnvelopeAmbiguityError as exc:
        raise UsageError(
            "multiple top-level frontmatter keys; pass --envelope to designate the "
            f"softschema payload (candidates: {', '.join(exc.candidates)})"
        ) from exc


def _compile_cmd(args: argparse.Namespace) -> int:
    # Model-load and compile errors (UsageError, OSError, ...) propagate to the shared
    # `_run_cmd` boundary, which reports them as `softschema compile: ...` and exits 2.
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
    # Reads under the same profile detection as `validate`, so the two never disagree
    # about what a given file is. `has_frontmatter` stays literal: a pure-yaml artifact
    # has none, and `profile` is what explains its populated metadata.
    read = _read_artifact(args.path, _profile_from_args(args))
    metadata = None
    envelope_keys: list[str] = []
    if isinstance(read.document, dict):
        metadata = parse_schema_metadata(read.document.get("softschema"))
        envelope_keys = [str(key) for key in read.document if key != "softschema"]
    print(
        _json(
            {
                "path": args.path,
                "profile": read.profile,
                "has_frontmatter": read.profile is SchemaProfile.frontmatter_md
                and read.document is not None,
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


SKILL_INSTALL_TARGETS: dict[str, Path] = {
    "portable": Path(".agents/skills/softschema/SKILL.md"),
    "claude": Path(".claude/skills/softschema/SKILL.md"),
}

_SKILL_MARKER = (
    "<!-- DO NOT EDIT format=f02: written by `softschema skill --install`.\n"
    "Re-run that command to update.\n-->\n"
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
                lines.insert(i + 1, _SKILL_MARKER)
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


def _is_managed_skill(existing: str) -> bool:
    return _SKILL_MARKER in existing


def _install_skill(base_dir: Path, *, agents: list[str], dry_run: bool = False) -> dict[str, Any]:
    payload_source = _rendered_skill_text()
    payload = _install_skill_payload(payload_source)
    files: list[dict[str, str]] = []
    pending: list[tuple[Path, str]] = []
    for agent in dict.fromkeys(agents):
        relative = SKILL_INSTALL_TARGETS[agent]
        target = base_dir / relative
        existing = target.read_text(encoding="utf-8") if target.exists() else None
        if existing == payload:
            status = "unchanged"
        elif existing is not None and not _is_managed_skill(existing):
            raise UsageError(f"refusing to overwrite unmanaged skill: {target}")
        else:
            status = "would_update" if existing is not None else "would_create"
            pending.append((target, "updated" if existing is not None else "created"))
        files.append({"path": str(relative), "status": status})
    if not dry_run:
        for target, final_status in pending:
            atomic_write_text(target, payload, make_parents=True)
            next(item for item in files if base_dir / item["path"] == target)["status"] = (
                final_status
            )
    return {
        "version": _installed_version(),
        "base_dir": str(base_dir),
        "dry_run": dry_run,
        "files": files,
    }


def _skill_cmd(args: argparse.Namespace) -> int:
    if args.install:
        if args.scope is None or not args.agents:
            raise UsageError(
                "skill --install requires --scope project|personal and at least one "
                "--agent portable|claude"
            )
        base = _resolve_install_base(Path.cwd()) if args.scope == "project" else Path.home()
        _write_text(_json(_install_skill(base, agents=args.agents, dry_run=args.dry_run)))
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
    module = Path(__file__).resolve()
    if len(module.parents) <= 4:
        return None
    root = module.parents[4]
    expected = root / "packages/python/src/softschema/cli.py"
    if expected.is_file() and expected.samefile(module) and (root / "pyproject.toml").is_file():
        candidate = root / relative_path
        return candidate if candidate.is_file() else None
    return None


def _write_text(text: str) -> None:
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")


def _json(value: Any) -> str:
    # Keep non-ASCII text readable and sort keys for stable diffs within this runtime.
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
