"""Command-line interface for softschema."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, cast

from frontmatter_format import fmf_read
from pydantic import BaseModel, ValidationError

from softschema.compile import compile_model
from softschema.models import SchemaBinding, Status, parse_document_metadata
from softschema.validate import validate_artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="softschema")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate an artifact.")
    validate_parser.add_argument("path", type=Path)
    validate_parser.add_argument("--contract", help="Override the document contract ID.")
    validate_parser.add_argument("--envelope", help="Override the inferred envelope key.")
    validate_parser.add_argument("--model", help="Pydantic model as module:Class.")
    validate_parser.add_argument("--schema", type=Path, help="JSON Schema YAML sidecar.")
    validate_parser.add_argument(
        "--status",
        choices=[status.value for status in Status],
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

    args = parser.parse_args(argv)
    return args.func(args)


def _validate_cmd(args: argparse.Namespace) -> int:
    try:
        contract_id, status, envelope_key = _infer_validation_binding(args)
        model = _load_model(args.model) if args.model else None
    except (TypeError, ValueError, ValidationError) as exc:
        print(f"softschema validate: {exc}", file=sys.stderr)
        return 2
    binding = SchemaBinding(
        contract_id=contract_id,
        model=model,
        envelope_key=envelope_key,
        schema_path=args.schema,
        status=status,
    )
    result = validate_artifact(args.path, binding=binding)
    print(_json(result))
    return 0 if result.ok else 1


def _infer_validation_binding(args: argparse.Namespace) -> tuple[str, Status, str | None]:
    _content, frontmatter = fmf_read(args.path)
    if not isinstance(frontmatter, dict):
        if args.contract is None:
            raise ValueError("missing --contract because the document has no YAML frontmatter")
        return args.contract, _status_from_args(args, None), args.envelope

    metadata = parse_document_metadata(frontmatter.get("softschema"))
    contract_id = args.contract or (metadata.contract_id if metadata is not None else None)
    if contract_id is None:
        raise ValueError("missing --contract because the document has no softschema.contract")

    return contract_id, _status_from_args(args, metadata), _envelope_from_args(args, frontmatter)


def _status_from_args(args: argparse.Namespace, metadata: Any) -> Status:
    if args.status is not None:
        return Status(args.status)
    if metadata is not None and metadata.status is not None:
        return metadata.status
    return Status.soft


def _envelope_from_args(args: argparse.Namespace, frontmatter: dict[str, Any]) -> str | None:
    if args.envelope is not None:
        return args.envelope
    envelope_keys = [str(key) for key in frontmatter if key != "softschema"]
    if len(envelope_keys) == 1:
        return envelope_keys[0]
    if not envelope_keys:
        return None
    raise ValueError(
        "missing --envelope because the document has multiple non-softschema "
        f"frontmatter keys: {', '.join(envelope_keys)}"
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
        metadata = parse_document_metadata(frontmatter.get("softschema"))
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


def _json(value: Any) -> str:
    return json.dumps(_plain(value), indent=2, sort_keys=True)


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
