"""Build and verify the immutable HTTPS schema publication candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

DRAFT_VOCABULARY_URI = "urn:softschema:draft:vocabulary:x-softschema:v0"
DRAFT_SCHEMA_ID_PATTERN = "^urn:softschema:draft:conformance:[a-z0-9-]+:v0$"
ALLOWED_CONTENT_TYPES = frozenset({"application/json", "application/schema+json"})
PUBLICATION_ROOT = "https://jlevy.github.io/softschema/"
TARGET_NAMESPACE = "https://jlevy.github.io/softschema/schema/v1/"
SOURCE_IDENTIFIER_STATUS = "draft-until-live-verification"
PUBLICATION_VERSION = "v1"
PUBLICATION_INDEX_FORMAT = "softschema-schema-publication-v1"
NAMESPACE_INDEX_FORMAT = "softschema-pages-namespace-v1"
NAMESPACE_INDEX_PATH = "publication-index.json"
NAMESPACE_INDEX_URL = f"{PUBLICATION_ROOT}{NAMESPACE_INDEX_PATH}"
DEFAULT_PROMOTION_MARKER = Path(__file__).with_name("publication-promoted.sha256")
MAX_PUBLISHED_SCHEMA_BYTES = 16 * 1024 * 1024
MAX_PUBLICATION_CONFIG_BYTES = 64 * 1024
MAX_PUBLICATION_INDEX_BYTES = 4 * 1024 * 1024
MAX_NAMESPACE_INDEX_BYTES = 8 * 1024 * 1024
MAX_PROMOTION_MARKER_BYTES = 65
MAX_PUBLISHED_SCHEMAS = 256
MAX_NAMESPACE_FILES = 4096
MAX_PUBLICATION_BUNDLE_BYTES = 64 * 1024 * 1024
MAX_NAMESPACE_BUNDLE_BYTES = 256 * 1024 * 1024
MAX_NAMESPACE_PATH_BYTES = 1024
MAX_NAMESPACE_PATH_DEPTH = 32
MAX_CONTENT_TYPES_PER_FILE = 8
PUBLICATION_FETCH_TIMEOUT_SECONDS = 30
MAX_JSON_DEPTH = 128
MAX_JSON_NODES = 100_000
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_SCHEMA_FILENAME_PATTERN = re.compile(r"[a-z0-9-]+\.schema\.json")
_CONTENT_TYPE_PATTERN = re.compile(r"[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*")
_NAMESPACE_PATH_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)*")
_EXPECTED_PUBLICATION_CONFIG: dict[str, Any] = {
    "schema_version": "1",
    "target_namespace": TARGET_NAMESPACE,
    "version": PUBLICATION_VERSION,
    "source_identifier_status": SOURCE_IDENTIFIER_STATUS,
    "promotion_gate": {
        "status": "external-verification-required",
        "http_status": 200,
        "redirects": 0,
        "content_types": ["application/json", "application/schema+json"],
        "digest": "sha256-byte-equality",
    },
}
_INDEX_FIELDS = {"format", "source_identifier_status", "target_namespace", "version", "schemas"}
_ENTRY_FIELDS = {"id", "path", "sha256", "size", "url"}
_NAMESPACE_FIELDS = {"files", "format"}
_NAMESPACE_ENTRY_FIELDS = {"content_types", "path", "sha256", "size"}
_SCHEMA_MAP_KEYWORDS = frozenset(
    {"$defs", "definitions", "dependentSchemas", "patternProperties", "properties"}
)
_SCHEMA_ARRAY_KEYWORDS = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
_SCHEMA_VALUE_KEYWORDS = frozenset(
    {
        "additionalProperties",
        "contains",
        "contentSchema",
        "else",
        "if",
        "items",
        "not",
        "propertyNames",
        "then",
        "unevaluatedItems",
        "unevaluatedProperties",
    }
)
_IDENTIFIER_VALUE_KEYWORDS = frozenset({"$dynamicRef", "$id", "$ref", "$schema"})
_TraversalContext = Literal["generic", "schema", "schema-array", "schema-map", "vocabulary"]


class PublicationError(RuntimeError):
    """A deterministic candidate-build or live-verification failure."""


def _bounded_confined_bytes(
    path: Path,
    *,
    root: Path,
    max_bytes: int,
    description: str,
) -> bytes:
    """Read one regular file after confinement and byte-size checks."""
    root = root.resolve()
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise PublicationError(f"{description} is missing or escapes its root: {path}") from exc
    if path.is_symlink() or not resolved.is_file():
        raise PublicationError(f"{description} is not a regular file: {path}")
    size = resolved.stat().st_size
    if size > max_bytes:
        raise PublicationError(f"{description} exceeds the byte limit: {path}")
    with resolved.open("rb") as stream:
        data = stream.read(max_bytes + 1)
    if len(data) != size:
        raise PublicationError(f"{description} changed while reading: {path}")
    return data


def _strict_json(
    path: Path,
    *,
    root: Path,
    max_bytes: int,
    description: str,
) -> Any:
    try:
        data = _bounded_confined_bytes(
            path,
            root=root,
            max_bytes=max_bytes,
            description=description,
        )
    except PublicationError:
        raise
    except OSError as exc:
        raise PublicationError(f"cannot read strict JSON from {path}: {exc}") from exc
    return _strict_json_bytes(data, description=str(path))


def _strict_json_bytes(data: bytes, *, description: str) -> Any:
    """Parse bounded bytes with the strict publication JSON policy."""

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise PublicationError(f"{description}: duplicate JSON key {key!r}")
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise PublicationError(f"{description}: non-finite JSON number {value}")

    def parse_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            reject_constant(value)
        return parsed

    try:
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
            parse_float=parse_float,
        )
        _validate_json_structure(value)
        return value
    except PublicationError:
        raise
    except (UnicodeError, RecursionError, ValueError) as exc:
        raise PublicationError(f"cannot parse strict JSON for {description}: {exc}") from exc


def _validate_json_structure(value: Any) -> None:
    """Apply the portable depth/node budget without recursive Python calls."""
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise PublicationError("strict JSON exceeds the depth limit")
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise PublicationError("strict JSON exceeds the node limit")
        if isinstance(current, str):
            try:
                current.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise PublicationError(
                    "strict JSON contains an invalid Unicode scalar value"
                ) from exc
        elif isinstance(current, dict):
            for key in current:
                try:
                    key.encode("utf-8", errors="strict")
                except UnicodeEncodeError as exc:
                    raise PublicationError(
                        "strict JSON contains an invalid Unicode scalar key"
                    ) from exc
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _assert_exact_json(value: Any, expected: Any, location: str) -> None:
    if type(value) is not type(expected):
        raise PublicationError(f"{location} has the wrong type")
    if isinstance(expected, dict):
        if set(value) != set(expected):
            raise PublicationError(f"{location} has unexpected fields")
        for key, expected_item in expected.items():
            _assert_exact_json(value[key], expected_item, f"{location}.{key}")
        return
    if isinstance(expected, list):
        if len(value) != len(expected):
            raise PublicationError(f"{location} has the wrong length")
        for index, expected_item in enumerate(expected):
            _assert_exact_json(value[index], expected_item, f"{location}[{index}]")
        return
    if value != expected:
        raise PublicationError(f"{location} has an unsupported value")


def _validate_publication_config(value: Any) -> dict[str, Any]:
    _assert_exact_json(value, _EXPECTED_PUBLICATION_CONFIG, "publication config")
    return cast(dict[str, Any], value)


def _replace_identifier(value: str, replacements: dict[str, str]) -> str:
    for source, target in replacements.items():
        if value == source or value.startswith(f"{source}#"):
            return f"{target}{value[len(source) :]}"
    return value


def _replace_required_identifier(value: str, replacements: dict[str, str]) -> str:
    replaced = _replace_identifier(value, replacements)
    if replaced.startswith("urn:softschema:draft:"):
        raise PublicationError(f"unresolved draft identifier in publication candidate: {value}")
    return replaced


def _replace_identifiers(
    value: Any,
    replacements: dict[str, str],
    *,
    _context: _TraversalContext = "schema",
) -> Any:
    if isinstance(value, list):
        item_context: _TraversalContext = "schema" if _context == "schema-array" else "generic"
        return [_replace_identifiers(item, replacements, _context=item_context) for item in value]
    if isinstance(value, dict):
        replaced: dict[str, Any] = {}
        for key, item in value.items():
            output_key = (
                _replace_required_identifier(key, replacements) if _context == "vocabulary" else key
            )
            if output_key in replaced:
                raise PublicationError(
                    f"identifier replacement creates duplicate mapping key: {output_key}"
                )
            if _context == "schema" and key in _IDENTIFIER_VALUE_KEYWORDS:
                replaced[output_key] = (
                    _replace_required_identifier(item, replacements)
                    if isinstance(item, str)
                    else item
                )
                continue
            if _context == "schema" and (
                (key == "const" and item == DRAFT_VOCABULARY_URI)
                or (key == "pattern" and item == DRAFT_SCHEMA_ID_PATTERN)
            ):
                replaced[output_key] = _replace_identifier(cast(str, item), replacements)
                continue
            item_context = "generic"
            if _context == "schema-map":
                item_context = "schema"
            elif _context == "schema":
                if key == "$vocabulary":
                    item_context = "vocabulary"
                elif key in _SCHEMA_MAP_KEYWORDS:
                    item_context = "schema-map"
                elif key in _SCHEMA_ARRAY_KEYWORDS:
                    item_context = "schema-array"
                elif key in _SCHEMA_VALUE_KEYWORDS:
                    item_context = "schema"
            replaced[output_key] = _replace_identifiers(
                item,
                replacements,
                _context=item_context,
            )
        return replaced
    if not isinstance(value, str):
        return value
    return value


def _preflight_immutable(path: Path, data: bytes) -> None:
    """Reject a conflicting versioned path before any candidate file is written."""
    if path.is_symlink():
        raise PublicationError(f"refusing to replace versioned candidate bytes: {path}")
    if not path.exists():
        return
    if not path.is_file() or path.stat().st_size != len(data):
        raise PublicationError(f"refusing to replace versioned candidate bytes: {path}")
    with path.open("rb") as stream:
        existing = stream.read(len(data) + 1)
    if existing != data:
        raise PublicationError(f"refusing to replace versioned candidate bytes: {path}")


def _write_immutable(path: Path, data: bytes) -> None:
    _preflight_immutable(path, data)
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _validate_namespace_path(path: str, *, location: str) -> None:
    parts = path.split("/")
    if (
        len(path.encode("utf-8")) > MAX_NAMESPACE_PATH_BYTES
        or len(parts) > MAX_NAMESPACE_PATH_DEPTH
        or path == NAMESPACE_INDEX_PATH
        or _NAMESPACE_PATH_PATTERN.fullmatch(path) is None
    ):
        raise PublicationError(f"{location} is unsafe or noncanonical")


def _build_namespace_index(
    files: dict[str, bytes],
    *,
    content_types: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Build the canonical inventory for every deployable Pages file."""
    entries: list[dict[str, Any]] = []
    default_types = sorted(ALLOWED_CONTENT_TYPES)
    for path, data in sorted(files.items()):
        entries.append(
            {
                "content_types": (
                    default_types
                    if content_types is None
                    else content_types.get(path, default_types)
                ),
                "path": path,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
        )
    return _validate_namespace_index(
        {
            "files": entries,
            "format": NAMESPACE_INDEX_FORMAT,
        }
    )


def _validate_namespace_index(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _NAMESPACE_FIELDS:
        raise PublicationError("namespace index has unexpected fields")
    namespace = cast(dict[str, Any], value)
    _assert_exact_json(namespace["format"], NAMESPACE_INDEX_FORMAT, "namespace index.format")
    entries = namespace["files"]
    if not isinstance(entries, list) or not entries or len(entries) > MAX_NAMESPACE_FILES:
        raise PublicationError("namespace index has an invalid file count")

    previous_path = ""
    total_size = 0
    for index, raw_entry in enumerate(cast(list[Any], entries)):
        location = f"namespace index.files[{index}]"
        if not isinstance(raw_entry, dict) or set(raw_entry) != _NAMESPACE_ENTRY_FIELDS:
            raise PublicationError(f"{location} has unexpected fields")
        entry = cast(dict[str, Any], raw_entry)
        path = entry["path"]
        if not isinstance(path, str):
            raise PublicationError(f"{location}.path has the wrong type")
        _validate_namespace_path(path, location=f"{location}.path")
        if path <= previous_path:
            raise PublicationError("namespace index paths are not unique and sorted")
        previous_path = path
        size = entry["size"]
        if type(size) is not int or not 0 <= size <= MAX_NAMESPACE_BUNDLE_BYTES:
            raise PublicationError(f"{location}.size is invalid")
        total_size += size
        if total_size > MAX_NAMESPACE_BUNDLE_BYTES:
            raise PublicationError("namespace index exceeds the aggregate byte limit")
        digest = entry["sha256"]
        if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
            raise PublicationError(f"{location}.sha256 is invalid")
        raw_content_types = entry["content_types"]
        if (
            not isinstance(raw_content_types, list)
            or not raw_content_types
            or len(raw_content_types) > MAX_CONTENT_TYPES_PER_FILE
            or any(
                not isinstance(content_type, str)
                or _CONTENT_TYPE_PATTERN.fullmatch(content_type) is None
                for content_type in raw_content_types
            )
            or raw_content_types != sorted(set(raw_content_types))
        ):
            raise PublicationError(f"{location}.content_types is invalid")
    return namespace


def _namespace_entries(namespace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        cast(str, entry["path"]): entry for entry in cast(list[dict[str, Any]], namespace["files"])
    }


def _preflight_candidate_path(root: Path, path: Path, data: bytes) -> None:
    """Confine a candidate path and reject every pre-existing symlink component."""
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise PublicationError(f"candidate path escapes output: {path}") from exc
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise PublicationError(f"candidate path uses a symlinked component: {path}")
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise PublicationError(f"candidate path escapes output: {path}") from exc
    _preflight_immutable(path, data)


def _check_candidate_inventory(
    output: Path,
    namespace: dict[str, Any],
    *,
    require_all: bool,
) -> None:
    """Reject every local node outside the generated candidate inventory."""
    expected_files = {
        NAMESPACE_INDEX_PATH,
        *(cast(str, entry["path"]) for entry in namespace["files"]),
    }
    expected_directories: set[str] = set()
    for relative in expected_files:
        parent = PurePosixPath(relative).parent
        while parent != PurePosixPath("."):
            expected_directories.add(parent.as_posix())
            parent = parent.parent
    if not output.exists():
        if require_all:
            raise PublicationError("candidate output directory is missing")
        return
    if output.is_symlink() or not output.is_dir():
        raise PublicationError("candidate output is not a regular directory")
    observed_files: set[str] = set()
    try:
        for path in output.rglob("*"):
            relative = path.relative_to(output).as_posix()
            if path.is_symlink():
                raise PublicationError(f"candidate output contains a symlink: {relative}")
            if path.is_file():
                if relative not in expected_files:
                    raise PublicationError(
                        f"candidate output contains an undeclared file: {relative}"
                    )
                observed_files.add(relative)
            elif path.is_dir():
                if relative not in expected_directories:
                    raise PublicationError(
                        f"candidate output contains an undeclared directory: {relative}"
                    )
            else:
                raise PublicationError(f"candidate output contains a special node: {relative}")
    except OSError as exc:
        raise PublicationError(f"cannot inspect candidate output inventory: {exc}") from exc
    if require_all and observed_files != expected_files:
        raise PublicationError(
            f"candidate output inventory is incomplete: {sorted(expected_files - observed_files)}"
        )


def build_publication_candidate(conformance: Path, output: Path) -> dict[str, Any]:
    """Generate final-identifier candidate bytes without mutating draft source files."""
    conformance = conformance.resolve()
    output = output.resolve()
    config = _validate_publication_config(
        _strict_json(
            conformance / "publication.json",
            root=conformance,
            max_bytes=MAX_PUBLICATION_CONFIG_BYTES,
            description="publication config",
        )
    )
    base_url = TARGET_NAMESPACE

    schemas: list[tuple[Path, dict[str, Any]]] = []
    source_ids: set[str] = set()
    source_bytes = 0
    replacements: dict[str, str] = {
        DRAFT_VOCABULARY_URI: f"{base_url}vocab/x-softschema",
        DRAFT_SCHEMA_ID_PATTERN: (f"^{re.escape(base_url)}[a-z0-9-]+\\.schema\\.json$"),
    }
    for source in sorted((conformance / "schemas").glob("*.schema.json")):
        if _SCHEMA_FILENAME_PATTERN.fullmatch(source.name) is None:
            raise PublicationError(f"source schema filename is noncanonical: {source.name}")
        source_bytes += source.stat().st_size
        if source_bytes > MAX_PUBLICATION_BUNDLE_BYTES:
            raise PublicationError("publication source bundle exceeds the byte limit")
        schema = _strict_json(
            source,
            root=conformance,
            max_bytes=MAX_PUBLISHED_SCHEMA_BYTES,
            description="source schema",
        )
        if not isinstance(schema, dict):
            raise PublicationError(f"schema root must be an object: {source.name}")
        schema_id = schema.get("$id")
        if (
            not isinstance(schema_id, str)
            or re.fullmatch(DRAFT_SCHEMA_ID_PATTERN, schema_id) is None
        ):
            raise PublicationError(f"source schema is not a draft candidate: {source.name}")
        if schema_id in source_ids:
            raise PublicationError(f"duplicate source schema id: {schema_id}")
        source_ids.add(schema_id)
        replacements[schema_id] = f"{base_url}{source.name}"
        schemas.append((source, schema))
        if len(schemas) > MAX_PUBLISHED_SCHEMAS:
            raise PublicationError("publication contains too many schemas")

    entries: list[dict[str, Any]] = []
    candidate_files: list[tuple[Path, bytes]] = []
    candidate_bytes = 0
    for source, schema in schemas:
        candidate = _replace_identifiers(schema, replacements)
        data = _json_bytes(candidate)
        candidate_bytes += len(data)
        if candidate_bytes > MAX_PUBLICATION_BUNDLE_BYTES:
            raise PublicationError("publication candidate bundle exceeds the byte limit")
        relative = Path("schema") / "v1" / source.name
        candidate_files.append((output / relative, data))
        entries.append(
            {
                "id": candidate["$id"],
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
                "url": f"{base_url}{source.name}",
            }
        )

    index = {
        "format": PUBLICATION_INDEX_FORMAT,
        "source_identifier_status": config["source_identifier_status"],
        "target_namespace": base_url,
        "version": config["version"],
        "schemas": entries,
    }
    validated_index = _validate_live_index(index)
    candidate_files.append((output / "schema" / "v1" / "index.json", _json_bytes(validated_index)))
    namespace = _build_namespace_index(
        {path.relative_to(output).as_posix(): data for path, data in candidate_files}
    )
    candidate_files.append((output / NAMESPACE_INDEX_PATH, _json_bytes(namespace)))
    _check_candidate_inventory(output, namespace, require_all=False)
    for path, data in candidate_files:
        _preflight_candidate_path(output, path, data)
    for path, data in candidate_files:
        _write_immutable(path, data)
    _check_candidate_inventory(output, namespace, require_all=True)
    return validated_index


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(  # pyright: ignore[reportImplicitOverride]
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _fetch_published_bytes(
    opener: Any,
    url: str,
    *,
    max_bytes: int,
    allow_missing: bool = False,
    allowed_content_types: frozenset[str] = ALLOWED_CONTENT_TYPES,
) -> bytes | None:
    """Fetch one fixed-origin JSON resource with no redirects and a hard byte cap."""
    request = urllib.request.Request(url, method="GET")
    try:
        with opener.open(request, timeout=PUBLICATION_FETCH_TIMEOUT_SECONDS) as response:
            status = response.status
            content_type = response.headers.get_content_type()
            body = response.read(max_bytes + 1)
            final_url = response.url
    except urllib.error.HTTPError as exc:
        if allow_missing and exc.code == 404 and exc.url == url:
            return None
        raise PublicationError(f"cannot fetch {url}: HTTP {exc.code}") from exc
    except (OSError, urllib.error.URLError) as exc:
        raise PublicationError(f"cannot fetch {url}: {exc}") from exc
    if status != 200 or final_url != url:
        raise PublicationError(f"live URL redirected or returned non-200: {url}")
    if content_type not in allowed_content_types:
        raise PublicationError(f"unexpected content type for {url}: {content_type}")
    if len(body) > max_bytes:
        raise PublicationError(f"live body exceeds the byte limit: {url}")
    return body


def _validate_live_index(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PublicationError("candidate index has unexpected fields")
    index_object = cast(dict[str, Any], value)
    if set(index_object) != _INDEX_FIELDS:
        raise PublicationError("candidate index has unexpected fields")
    expected_header = {
        "format": PUBLICATION_INDEX_FORMAT,
        "source_identifier_status": SOURCE_IDENTIFIER_STATUS,
        "target_namespace": TARGET_NAMESPACE,
        "version": PUBLICATION_VERSION,
    }
    for field, expected in expected_header.items():
        _assert_exact_json(index_object[field], expected, f"candidate index.{field}")
    entries = index_object["schemas"]
    if not isinstance(entries, list) or not entries or len(entries) > MAX_PUBLISHED_SCHEMAS:
        raise PublicationError("candidate index has an invalid schema count")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    seen_urls: set[str] = set()
    for index, raw_entry in enumerate(cast(list[Any], entries)):
        location = f"candidate index.schemas[{index}]"
        if not isinstance(raw_entry, dict):
            raise PublicationError(f"{location} has unexpected fields")
        entry = cast(dict[str, Any], raw_entry)
        if set(entry) != _ENTRY_FIELDS:
            raise PublicationError(f"{location} has unexpected fields")
        path = entry["path"]
        if not isinstance(path, str):
            raise PublicationError(f"{location}.path has the wrong type")
        parts = path.split("/")
        if (
            "\\" in path
            or PurePosixPath(path).is_absolute()
            or any(part in {"", ".", ".."} for part in parts)
            or len(parts) != 3
            or parts[:2] != ["schema", "v1"]
            or _SCHEMA_FILENAME_PATTERN.fullmatch(parts[2]) is None
        ):
            raise PublicationError(f"{location}.path is unsafe or noncanonical")
        expected_url = f"{TARGET_NAMESPACE}{parts[2]}"
        for field in ("id", "url"):
            if entry[field] != expected_url:
                raise PublicationError(f"{location}.{field} does not match the candidate path")
        size = entry["size"]
        if type(size) is not int or not 0 < size <= MAX_PUBLISHED_SCHEMA_BYTES:
            raise PublicationError(f"{location}.size is invalid")
        digest = entry["sha256"]
        if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
            raise PublicationError(f"{location}.sha256 is invalid")
        for seen, field in (
            (seen_ids, "id"),
            (seen_paths, "path"),
            (seen_urls, "url"),
        ):
            item = entry[field]
            if item in seen:
                raise PublicationError(f"candidate index has duplicate {field}: {item}")
            seen.add(item)
    return index_object


def _read_candidate_file(output: Path, relative: str, expected_size: int) -> bytes:
    output_root = output.resolve()
    path = output.joinpath(*relative.split("/"))
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(output_root)
    except (OSError, ValueError) as exc:
        raise PublicationError(f"candidate path is missing or escapes output: {relative}") from exc
    if path.is_symlink() or not path.is_file():
        raise PublicationError(f"candidate path is not a regular file: {relative}")
    if path.stat().st_size != expected_size:
        raise PublicationError(f"candidate size differs from index: {relative}")
    with path.open("rb") as stream:
        data = stream.read(expected_size + 1)
    if len(data) != expected_size:
        raise PublicationError(f"candidate size changed while reading: {relative}")
    return data


def _load_candidate_index(output: Path) -> tuple[dict[str, Any], bytes]:
    output = output.resolve()
    namespace, _namespace_bytes = _load_namespace_index(output)
    index_path = output / "schema" / "v1" / "index.json"
    index = _validate_live_index(
        _strict_json(
            index_path,
            root=output,
            max_bytes=MAX_PUBLICATION_INDEX_BYTES,
            description="candidate index",
        )
    )
    index_bytes = _bounded_confined_bytes(
        index_path,
        root=output,
        max_bytes=MAX_PUBLICATION_INDEX_BYTES,
        description="candidate index",
    )
    if index_bytes != _json_bytes(index):
        raise PublicationError("candidate index is not canonical JSON")
    namespace_entries = _namespace_entries(namespace)
    expected_paths = {
        "schema/v1/index.json",
        *(cast(str, entry["path"]) for entry in index["schemas"]),
    }
    if not expected_paths.issubset(namespace_entries):
        raise PublicationError("candidate namespace omits a v1 index path")
    for relative in expected_paths:
        entry = namespace_entries[relative]
        data = _read_candidate_file(output, relative, cast(int, entry["size"]))
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise PublicationError(f"candidate digest differs from namespace index: {relative}")
    for entry in index["schemas"]:
        namespace_entry = namespace_entries[entry["path"]]
        if namespace_entry["size"] != entry["size"] or namespace_entry["sha256"] != entry["sha256"]:
            raise PublicationError(
                f"candidate v1 index conflicts with namespace index: {entry['path']}"
            )
    return index, index_bytes


def _load_namespace_index(output: Path) -> tuple[dict[str, Any], bytes]:
    output = output.resolve()
    namespace_path = output / NAMESPACE_INDEX_PATH
    namespace = _validate_namespace_index(
        _strict_json(
            namespace_path,
            root=output,
            max_bytes=MAX_NAMESPACE_INDEX_BYTES,
            description="candidate namespace index",
        )
    )
    namespace_bytes = _bounded_confined_bytes(
        namespace_path,
        root=output,
        max_bytes=MAX_NAMESPACE_INDEX_BYTES,
        description="candidate namespace index",
    )
    if namespace_bytes != _json_bytes(namespace):
        raise PublicationError("candidate namespace index is not canonical JSON")
    _check_candidate_inventory(output, namespace, require_all=True)
    for entry in namespace["files"]:
        relative = cast(str, entry["path"])
        data = _read_candidate_file(output, relative, cast(int, entry["size"]))
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise PublicationError(f"candidate digest differs from namespace index: {relative}")
    return namespace, namespace_bytes


def _load_promotion_digest(marker: Path | None) -> str | None:
    if marker is None:
        return None
    try:
        mode = marker.lstat().st_mode
        if not stat.S_ISREG(mode):
            raise PublicationError(f"promotion marker is not a regular file: {marker}")
        with marker.open("rb") as stream:
            data = stream.read(MAX_PROMOTION_MARKER_BYTES + 1)
    except FileNotFoundError:
        return None
    except PublicationError:
        raise
    except OSError as exc:
        raise PublicationError(f"cannot read promotion marker {marker}: {exc}") from exc
    if (
        len(data) != MAX_PROMOTION_MARKER_BYTES
        or data[-1:] != b"\n"
        or _SHA256_PATTERN.fullmatch(data[:-1].decode("ascii", errors="ignore")) is None
    ):
        raise PublicationError("promotion marker must be one lowercase SHA-256 digest")
    return data[:-1].decode("ascii")


def _published_namespace(data: bytes) -> dict[str, Any]:
    namespace = _validate_namespace_index(
        _strict_json_bytes(data, description="live namespace index")
    )
    if data != _json_bytes(namespace):
        raise PublicationError("live namespace index is not canonical JSON")
    return namespace


def _fetch_namespace_files(
    opener: Any,
    namespace: dict[str, Any],
) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for entry in namespace["files"]:
        relative = cast(str, entry["path"])
        url = f"{PUBLICATION_ROOT}{relative}"
        body = _fetch_published_bytes(
            opener,
            url,
            max_bytes=cast(int, entry["size"]),
            allowed_content_types=frozenset(cast(list[str], entry["content_types"])),
        )
        if body is None:  # defensive: namespace file fetches never permit absence
            raise PublicationError(f"live URL is unexpectedly missing: {url}")
        if len(body) != entry["size"]:
            raise PublicationError(f"live size differs from namespace index: {url}")
        if hashlib.sha256(body).hexdigest() != entry["sha256"]:
            raise PublicationError(f"live bytes differ from namespace index: {url}")
        files[relative] = body
    return files


def _write_merged_namespace(
    output: Path,
    namespace: dict[str, Any],
    retained_files: dict[str, bytes],
) -> None:
    for relative, data in retained_files.items():
        path = output.joinpath(*relative.split("/"))
        _preflight_candidate_path(output, path, data)
    for relative, data in retained_files.items():
        _write_immutable(output.joinpath(*relative.split("/")), data)
    namespace_path = output / NAMESPACE_INDEX_PATH
    if namespace_path.is_symlink() or not namespace_path.is_file():
        raise PublicationError("candidate namespace index is not a regular file")
    namespace_path.write_bytes(_json_bytes(namespace))
    _check_candidate_inventory(output, namespace, require_all=True)


def verify_predeploy_candidate(
    output: Path,
    *,
    promotion_marker: Path | None = None,
) -> dict[str, Any]:
    """Reconstruct the append-only live namespace and reject byte replacement."""
    output = output.resolve()
    index, _index_bytes = _load_candidate_index(output)
    candidate_namespace, _candidate_namespace_bytes = _load_namespace_index(output)
    candidate_entries = _namespace_entries(candidate_namespace)
    promotion_digest = _load_promotion_digest(promotion_marker)

    opener = urllib.request.build_opener(_NoRedirect())
    live_namespace_bytes = _fetch_published_bytes(
        opener,
        NAMESPACE_INDEX_URL,
        max_bytes=MAX_NAMESPACE_INDEX_BYTES,
        allow_missing=True,
    )
    if live_namespace_bytes is None:
        if promotion_digest is not None:
            raise PublicationError("promoted namespace index is unavailable")
        for entry in candidate_namespace["files"]:
            relative = cast(str, entry["path"])
            url = f"{PUBLICATION_ROOT}{relative}"
            if (
                _fetch_published_bytes(
                    opener,
                    url,
                    max_bytes=cast(int, entry["size"]),
                    allow_missing=True,
                    allowed_content_types=frozenset(cast(list[str], entry["content_types"])),
                )
                is not None
            ):
                raise PublicationError(f"live namespace is partial without an index: {url}")
        return {
            "files": len(candidate_entries),
            "ok": True,
            "schemas": len(index["schemas"]),
            "state": "absent",
            "target_namespace": index["target_namespace"],
        }

    if (
        promotion_digest is not None
        and hashlib.sha256(live_namespace_bytes).hexdigest() != promotion_digest
    ):
        raise PublicationError("live namespace index conflicts with the promotion marker")
    live_namespace = _published_namespace(live_namespace_bytes)
    live_entries = _namespace_entries(live_namespace)
    for relative in candidate_entries.keys() & live_entries.keys():
        if candidate_entries[relative] != live_entries[relative]:
            raise PublicationError(f"live path conflicts with the candidate: {relative}")
    live_files = _fetch_namespace_files(opener, live_namespace)
    retained_files = {
        relative: data for relative, data in live_files.items() if relative not in candidate_entries
    }
    merged_entries = {**live_entries, **candidate_entries}
    merged_namespace = _validate_namespace_index(
        {
            "files": [merged_entries[path] for path in sorted(merged_entries)],
            "format": NAMESPACE_INDEX_FORMAT,
        }
    )
    _write_merged_namespace(output, merged_namespace, retained_files)
    state = "extended" if candidate_entries.keys() - live_entries.keys() else "exact"
    return {
        "files": len(merged_entries),
        "ok": True,
        "schemas": len(index["schemas"]),
        "state": state,
        "target_namespace": index["target_namespace"],
    }


def verify_live_candidate(
    output: Path,
    *,
    promotion_marker: Path | None = None,
) -> dict[str, Any]:
    """Prove the complete namespace serves exact bytes without redirects."""
    output = output.resolve()
    index, _index_bytes = _load_candidate_index(output)
    namespace, namespace_bytes = _load_namespace_index(output)
    promotion_digest = _load_promotion_digest(promotion_marker)
    if (
        promotion_digest is not None
        and hashlib.sha256(namespace_bytes).hexdigest() != promotion_digest
    ):
        raise PublicationError("promotion marker conflicts with the candidate namespace index")
    opener = urllib.request.build_opener(_NoRedirect())
    live_namespace = _fetch_published_bytes(
        opener,
        NAMESPACE_INDEX_URL,
        max_bytes=MAX_NAMESPACE_INDEX_BYTES,
    )
    if live_namespace != namespace_bytes:
        raise PublicationError("live namespace index differs from the candidate")
    live_files = _fetch_namespace_files(opener, namespace)
    for relative, body in live_files.items():
        expected = _read_candidate_file(output, relative, len(body))
        if body != expected:
            raise PublicationError(f"live bytes differ from candidate: {relative}")
    return {
        "files": len(namespace["files"]),
        "ok": True,
        "schemas": len(index["schemas"]),
        "target_namespace": index["target_namespace"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="build the immutable static candidate")
    build.add_argument("output", type=Path)
    verify = commands.add_parser("verify-live", help="verify the deployed candidate")
    verify.add_argument("output", type=Path)
    verify.add_argument("--promotion-marker", type=Path)
    predeploy = commands.add_parser(
        "verify-predeploy",
        help="reconstruct the complete namespace and reject replacement",
    )
    predeploy.add_argument("output", type=Path)
    predeploy.add_argument(
        "--promotion-marker",
        type=Path,
        default=DEFAULT_PROMOTION_MARKER,
        help="reviewed v1 index digest; absence is allowed only while this file is absent",
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            result = build_publication_candidate(Path(__file__).resolve().parent, args.output)
        elif args.command == "verify-live":
            result = verify_live_candidate(
                args.output,
                promotion_marker=args.promotion_marker,
            )
        else:
            result = verify_predeploy_candidate(
                args.output,
                promotion_marker=args.promotion_marker,
            )
    except (OSError, PublicationError) as exc:
        print(f"softschema schema publication: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
