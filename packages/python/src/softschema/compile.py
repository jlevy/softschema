"""Pydantic-to-JSON-Schema compiler (emits compiled schema YAML)."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from frontmatter_format import new_yaml
from pydantic import BaseModel
from strif import atomic_write_bytes

from softschema._bounded_file import read_bounded_bytes
from softschema.canonicalize import canonicalize_json_schema
from softschema.core.value_domain import (
    DEFAULT_VALIDATION_LIMITS,
    PortableValueError,
    normalize_portable_value,
)
from softschema.models import validate_contract_id, validate_schema_id
from softschema.value_domain import parse_portable_yaml

# Version of the `x-softschema` block format emitted into compiled schemas,
# not the installed package version (use `importlib.metadata.version("softschema")`
# for that). Bump this only when the shape of `x-softschema` itself changes.
SOFTSCHEMA_FORMAT_VERSION = "0.1.0"
JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
ROOT_COMPILER_METADATA_RESERVED_MESSAGE = (
    "model schema root must not define reserved x-softschema metadata"
)


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
    checked_contract_id = validate_contract_id(contract_id)
    checked_schema_id = validate_schema_id(schema_id) if schema_id is not None else None
    canonical_schema = canonicalize_json_schema(
        _augment_schema(
            model_cls.model_json_schema(),
            checked_contract_id,
            checked_schema_id,
        )
    )
    # JSON has one number type, while Python distinguishes integral floats from
    # integers and JavaScript does not. Normalize the complete compiled value before
    # hashing and rendering so semantically equal bounds such as ``10.0`` and ``10``
    # have one portable representation in every implementation. This boundary also
    # rejects values (for example non-finite or unsafe integers) that cannot retain an
    # exact language-neutral JSON meaning.
    normalized_schema, _size = normalize_portable_value(canonical_schema)
    if not isinstance(normalized_schema, dict):  # defensive: the compiler always builds a map
        raise TypeError("compiled schema root must be a mapping")
    schema = normalized_schema
    schema_sha256 = _schema_sha256(schema)
    compiler_metadata = schema.get("x-softschema")
    if not isinstance(compiler_metadata, dict):  # defensive: ``_augment_schema`` owns this block
        raise TypeError("compiled schema metadata must be a mapping")
    compiler_metadata["schema_sha256"] = schema_sha256
    # The digest field is part of the emitted value even though it cannot be part of
    # its own preimage. Charge it against the same portable node/scalar budgets before
    # rendering so compiler output is always loadable by SchemaView.
    final_schema, _final_size = normalize_portable_value(schema)
    if not isinstance(final_schema, dict):  # defensive: metadata insertion keeps a map
        raise TypeError("compiled schema root must be a mapping")
    schema = final_schema
    rendered = _render_schema_within_limit(schema)

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
        encoded = read_bounded_bytes(out_path, DEFAULT_VALIDATION_LIMITS.max_resource_bytes)
        existing = parse_portable_yaml(
            encoded.decode("utf-8-sig"),
            limits=DEFAULT_VALIDATION_LIMITS,
            encoded_size=len(encoded),
        )
        # Python considers ``True == 1``; canonical JSON does not. Compare the shared
        # language-neutral representation so boolean/number drift is never hidden.
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

    # Write the exact LF-normalized bytes whose size was checked above. Text-mode
    # Path.write_text translates newlines on Windows and could otherwise create an
    # artifact larger than the shared 8 MiB boundary after validation.
    atomic_write_bytes(out_path, rendered.encode("utf-8"), make_parents=True)
    return CompileResult(
        out_path=out_path,
        schema_yaml=rendered,
        drift=False,
        schema_sha256=schema_sha256,
    )


def _render_schema_within_limit(schema: dict[str, Any]) -> str:
    """Render a sidecar that both runtimes accept and bounded readers can reopen."""
    canonical_json = json.dumps(
        schema,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    limit = DEFAULT_VALIDATION_LIMITS.max_resource_bytes
    if len(canonical_json.encode("utf-8")) > limit:
        raise PortableValueError("maximum resource size exceeded")
    rendered = _yaml_dump(schema)
    # JSON is a YAML 1.2 document and is already the shared canonical byte form. A
    # runtime's human-readable YAML writer may add different wrapping, quoting, or
    # indentation overhead near the boundary; fall back to canonical JSON rather than
    # making compiler acceptance depend on that writer.
    return rendered if len(rendered.encode("utf-8")) <= limit else canonical_json


def _augment_schema(
    schema: dict[str, Any],
    contract_id: str,
    schema_id: str | None,
) -> dict[str, Any]:
    out = dict(schema)
    out.setdefault("$schema", JSON_SCHEMA_DRAFT)
    # Schema identity is controlled only by the explicit compiler option. A logical
    # contract ID is intentionally not a URI, and model configuration must not create
    # a second implicit identity boundary.
    out.pop("$id", None)
    if schema_id is not None:
        out["$id"] = schema_id
    # The root x-softschema block is language-neutral on purpose: no `generated_from`
    # provenance (a Pydantic/Zod-specific import path would leak the implementation and
    # break the cross-language content identity and equal schema_sha256).
    # It is also a reserved compiler boundary. Reject rather than silently merge or
    # discard model-supplied content, which could otherwise make official output fail
    # its own compiled-schema profile or diverge by runtime/type.
    if "x-softschema" in out:
        raise ValueError(ROOT_COMPILER_METADATA_RESERVED_MESSAGE)
    out["x-softschema"] = {
        "contract": contract_id,
        "softschema_format_version": SOFTSCHEMA_FORMAT_VERSION,
    }
    return out


def _schema_sha256(schema: dict[str, Any]) -> str:
    # ensure_ascii=False so the hash is over literal UTF-8 (matching the TypeScript
    # JSON.stringify); otherwise non-ASCII in descriptions would hash differently.
    canonical = _canonical_json(schema)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    """Return the shared canonical JSON spelling used for identity and drift."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _yaml_dump(schema: dict[str, Any]) -> str:
    # Canonical profile: keys sorted for deterministic byte output. Use
    # frontmatter-format's YAML (block style, clean multi-line scalars). Disable
    # its default empty/None suppression: a schema serializer must never drop a
    # field (e.g. an empty `properties` or a `null` enum member).
    writer = new_yaml(key_sort=str, suppress_vals=None, typ="safe")
    # TypeScript's canonical writer uses ``lineWidth: 0`` (no wrapping). Match that
    # policy rather than introducing runtime-specific continuation bytes near the
    # shared resource limit. This width is above every portable scalar and resource
    # budget while remaining within ruamel.yaml's integer interface.
    writer.width = 2**31 - 1
    buffer = io.StringIO()
    writer.dump(schema, buffer)
    return buffer.getvalue()
