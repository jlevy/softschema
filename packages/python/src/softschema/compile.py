"""Pydantic-to-JSON-Schema compiler (emits compiled schema YAML)."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from frontmatter_format import new_yaml, read_yaml_file
from pydantic import BaseModel
from strif import atomic_write_text

from softschema.canonicalize import canonicalize_json_schema

# Version of the `x-softschema` block format emitted into compiled schemas,
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
    """Compile ``model_cls`` to a compiled JSON Schema YAML file at ``out_path``."""
    schema = canonicalize_json_schema(_augment_schema(model_cls.model_json_schema(), contract_id))
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
        # Compare parsed content, not raw bytes, so YAML formatting differences (e.g.
        # a different writer in another implementation) are not treated as drift; only a
        # genuine schema change is.
        existing = read_yaml_file(out_path)
        if existing == schema:
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

    atomic_write_text(out_path, rendered, make_parents=True)
    return CompileResult(
        out_path=out_path,
        schema_yaml=rendered,
        drift=False,
        schema_sha256=schema_sha256,
    )


def _augment_schema(
    schema: dict[str, Any],
    contract_id: str | None,
) -> dict[str, Any]:
    out = dict(schema)
    out.setdefault("$schema", JSON_SCHEMA_DRAFT)
    if contract_id is not None:
        out.setdefault("$id", contract_id)
    # The root x-softschema block is language-neutral on purpose: no `generated_from`
    # provenance (a Pydantic/Zod-specific import path would leak the implementation and
    # break the cross-language content identity and equal schema_sha256).
    out.setdefault("x-softschema", {})
    out["x-softschema"].update(
        {
            "contract": contract_id,
            "softschema_format_version": SOFTSCHEMA_FORMAT_VERSION,
        }
    )
    return out


def _schema_sha256(schema: dict[str, Any]) -> str:
    # ensure_ascii=False so the hash is over literal UTF-8 (matching the TypeScript
    # JSON.stringify); otherwise non-ASCII in descriptions would hash differently.
    canonical = json.dumps(
        schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _yaml_dump(schema: dict[str, Any]) -> str:
    # Canonical profile: keys sorted for deterministic byte output. Use
    # frontmatter-format's YAML (block style, clean multi-line scalars). Disable
    # its default empty/None suppression: a schema serializer must never drop a
    # field (e.g. an empty `properties` or a `null` enum member).
    writer = new_yaml(key_sort=str, suppress_vals=None, typ="safe")
    # Wide width so long scalars (the 64-char schema_sha256, $refs) are never
    # wrapped onto continuation lines; keeps the compiled schema clean and the byte
    # output reproducible across implementations.
    writer.width = 4096
    buffer = io.StringIO()
    writer.dump(schema, buffer)
    return buffer.getvalue()
