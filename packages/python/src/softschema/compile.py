"""Pydantic to JSON Schema YAML sidecar emitter."""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

# Version of the `x-softschema` block format emitted into compiled sidecars,
# not the installed package version (use `importlib.metadata.version("softschema")`
# for that). Bump this only when the shape of `x-softschema` itself changes.
SOFTSCHEMA_FORMAT_VERSION = "0.1.0"
JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"


@dataclass(frozen=True)
class CompileResult:
    """Outcome of a compile pass."""

    out_path: Path
    schema_yaml: str
    drift: bool = False
    drift_diff: str | None = None
    schema_sha256: str | None = None


def compile_model(
    model_cls: type[BaseModel],
    out_path: Path,
    *,
    contract_id: str | None = None,
    check_only: bool = False,
) -> CompileResult:
    """Compile ``model_cls`` to a JSON Schema YAML sidecar at ``out_path``."""
    schema = _augment_schema(model_cls.model_json_schema(), model_cls, contract_id)
    schema_sha256 = _schema_sha256(schema)
    schema.setdefault("x-softschema", {})["schema_sha256"] = schema_sha256
    rendered = _yaml_dump(schema)

    if check_only:
        if not out_path.is_file():
            return CompileResult(
                out_path=out_path,
                schema_yaml=rendered,
                drift=True,
                drift_diff=f"missing committed schema sidecar at {out_path}",
                schema_sha256=schema_sha256,
            )
        existing = out_path.read_text()
        if existing.strip() == rendered.strip():
            return CompileResult(
                out_path=out_path,
                schema_yaml=rendered,
                drift=False,
                schema_sha256=schema_sha256,
            )
        return CompileResult(
            out_path=out_path,
            schema_yaml=rendered,
            drift=True,
            drift_diff=f"committed schema at {out_path} differs from compile output",
            schema_sha256=schema_sha256,
        )

    _write_atomic(out_path, rendered)
    return CompileResult(
        out_path=out_path,
        schema_yaml=rendered,
        drift=False,
        schema_sha256=schema_sha256,
    )


def _augment_schema(
    schema: dict[str, Any],
    model_cls: type[BaseModel],
    contract_id: str | None,
) -> dict[str, Any]:
    out = dict(schema)
    out.setdefault("$schema", JSON_SCHEMA_DRAFT)
    if contract_id is not None:
        out.setdefault("$id", contract_id)
    out.setdefault("x-softschema", {})
    out["x-softschema"].update(
        {
            "contract": contract_id,
            "generated_from": f"{model_cls.__module__}:{model_cls.__name__}",
            "softschema_format_version": SOFTSCHEMA_FORMAT_VERSION,
        }
    )
    return out


def _schema_sha256(schema: dict[str, Any]) -> str:
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _yaml_dump(schema: dict[str, Any]) -> str:
    return yaml.safe_dump(schema, sort_keys=False, default_flow_style=False, allow_unicode=True)


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)
