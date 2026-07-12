"""Pydantic-to-JSON-Schema compiler (emits compiled schema YAML)."""

from __future__ import annotations

import hashlib
import io
import json
import math
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from frontmatter_format import new_yaml
from pydantic import BaseModel
from strif import atomic_write_text

from softschema._portable import MAX_SAFE_INTEGER, parse_yaml, read_utf8
from softschema.canonicalize import canonicalize_json_schema
from softschema.models import _check_contract_id

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
    contract_id: str,
    schema_id: str | None = None,
    check_only: bool = False,
) -> CompileResult:
    """Compile ``model_cls`` to a compiled JSON Schema YAML file at ``out_path``."""
    _check_contract_id(contract_id)
    if schema_id is not None and not urlparse(schema_id).scheme:
        raise ValueError("schema_id must be an absolute URI")
    raw_schema = model_cls.model_json_schema()
    if model_cls.model_config.get("title") is None:
        raw_schema["title"] = _contract_name(contract_id)
    schema = canonicalize_json_schema(_augment_schema(raw_schema, contract_id, schema_id))
    schema_sha256 = _schema_sha256(schema)
    schema.setdefault("x-softschema", {})["schema_sha256"] = schema_sha256
    rendered = _yaml_dump(schema)

    if check_only:
        if not out_path.is_file():
            return CompileResult(
                out_path=out_path,
                schema_yaml=rendered,
                drift=True,
                drift_diff=f"missing committed compiled schema at {out_path}",
                schema_sha256=schema_sha256,
            )
        # Compare parsed content, not raw bytes, so YAML formatting differences (e.g.
        # a different writer in another implementation) are not treated as drift; only a
        # genuine schema change is.
        existing = parse_yaml(read_utf8(out_path))
        if _canonical_json(existing) == _canonical_json(schema):
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
    contract_id: str,
    schema_id: str | None,
) -> dict[str, Any]:
    if "x-softschema" in schema or "$id" in schema:
        raise ValueError("model schema uses a compiler-reserved root identity key")
    out = dict(schema)
    out.setdefault("$schema", JSON_SCHEMA_DRAFT)
    if schema_id is not None:
        out["$id"] = schema_id
    # The root x-softschema block is language-neutral on purpose: no `generated_from`
    # provenance (a Pydantic/Zod-specific import path would leak the implementation and
    # break the cross-language content identity and equal schema_sha256).
    out["x-softschema"] = {"contract": contract_id}
    return out


def _contract_name(contract_id: str) -> str:
    return contract_id.rsplit(":", 1)[-1].split("/", 1)[0]


def _schema_sha256(schema: dict[str, Any]) -> str:
    canonical = _canonical_json(schema)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    """Encode the portable value domain with RFC 8785 key and number rules."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise TypeError("canonical JSON integer exceeds the portable safe range")
        return str(value)
    if isinstance(value, float):
        return _canonical_float(value)
    if isinstance(value, list | tuple):
        return "[" + ",".join(_canonical_json(item) for item in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value, key=lambda key: str(key).encode("utf-16be"))
        return (
            "{"
            + ",".join(f"{_canonical_json(str(key))}:{_canonical_json(value[key])}" for key in keys)
            + "}"
        )
    raise TypeError(f"canonical JSON does not support {type(value).__name__}")


def _canonical_float(value: float) -> str:
    if not math.isfinite(value):
        raise TypeError("canonical JSON requires finite numbers")
    if value == 0:
        return "0"
    magnitude = abs(value)
    text = repr(value).lower()
    if value.is_integer() and magnitude < 1e21:
        return format(Decimal(text), "f").split(".", 1)[0]
    if 1e-6 <= magnitude < 1e21 and "e" in text:
        return format(Decimal(text), "f")
    if "e" not in text:
        return text
    mantissa, exponent = text.split("e")
    sign = "+" if not exponent.startswith("-") else "-"
    digits = exponent.lstrip("+-0") or "0"
    return f"{mantissa}e{sign}{digits}"


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
