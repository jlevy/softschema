from __future__ import annotations

import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch

from softschema import validate_structural

JSON_SCHEMA_2020_12 = "https://json-schema.org/draft/2020-12/schema"


def _reference_error(reference: str) -> dict[str, str]:
    return {
        "kind": "schema_invalid",
        "reason": "reference",
        "message": "compiled schema reference is unavailable offline",
        "schema_path": "/$ref",
        "reference": reference,
    }


def test_trusted_resources_resolve_relative_to_an_absolute_root_id(tmp_path: Path) -> None:
    schema = tmp_path / "root.schema.yaml"
    schema.write_text(
        (f"$schema: {JSON_SCHEMA_2020_12}\n$id: https://schemas.example/root\n$ref: child\n"),
        encoding="utf-8",
    )
    resources = {
        "https://schemas.example/child": {
            "$schema": JSON_SCHEMA_2020_12,
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        }
    }

    result = validate_structural({"name": "Ada"}, schema, resources=resources)

    assert result.ok is True


def test_trusted_resources_resolve_relative_to_their_mapping_uri(tmp_path: Path) -> None:
    schema = tmp_path / "root.schema.yaml"
    schema.write_text(
        (f"$schema: {JSON_SCHEMA_2020_12}\n$ref: https://schemas.example/bundle/root\n"),
        encoding="utf-8",
    )
    resources = {
        "https://schemas.example/bundle/root": {
            "$schema": JSON_SCHEMA_2020_12,
            "$ref": "child",
        },
        "https://schemas.example/bundle/child": {
            "$schema": JSON_SCHEMA_2020_12,
            "type": "string",
        },
    }

    assert validate_structural("Ada", schema, resources=resources).ok is True


def test_idless_root_has_no_implicit_relative_file_base(tmp_path: Path) -> None:
    schema = tmp_path / "root.schema.yaml"
    schema.write_text(
        f"$schema: {JSON_SCHEMA_2020_12}\n$ref: sibling.schema.json\n",
        encoding="utf-8",
    )
    resources = {
        "https://schemas.example/sibling.schema.json": {
            "$schema": JSON_SCHEMA_2020_12,
            "type": "object",
        }
    }

    result = validate_structural({}, schema, resources=resources)

    assert result.errors == [_reference_error("sibling.schema.json")]


def test_unresolved_http_reference_never_reaches_a_local_trap_server(tmp_path: Path) -> None:
    requests: list[str] = []

    class TrapHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            self.send_response(500)
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), TrapHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = server.server_address[0]
    port = server.server_address[1]
    reference = f"http://{host}:{port}/schema.json"
    schema = tmp_path / "root.schema.yaml"
    schema.write_text(
        f"$schema: {JSON_SCHEMA_2020_12}\n$ref: {reference}\n",
        encoding="utf-8",
    )

    try:
        result = validate_structural({}, schema)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

    assert result.errors == [_reference_error(reference)]
    assert requests == []


def test_unresolved_file_reference_never_calls_urlopen(tmp_path: Path) -> None:
    sibling = tmp_path / "sibling.schema.json"
    sibling.write_text('{"type": "object"}\n', encoding="utf-8")
    reference = sibling.as_uri()
    schema = tmp_path / "root.schema.yaml"
    schema.write_text(
        f"$schema: {JSON_SCHEMA_2020_12}\n$ref: {reference}\n",
        encoding="utf-8",
    )

    with patch.object(
        urllib.request,
        "urlopen",
        side_effect=AssertionError("schema retrieval must remain offline"),
    ) as urlopen:
        result = validate_structural({}, schema)

    assert result.errors == [_reference_error(reference)]
    urlopen.assert_not_called()


def test_supplied_resource_cannot_enable_transitive_retrieval(tmp_path: Path) -> None:
    schema = tmp_path / "root.schema.yaml"
    schema.write_text(
        f"$schema: {JSON_SCHEMA_2020_12}\n$ref: https://schemas.example/root\n",
        encoding="utf-8",
    )
    missing = "https://schemas.example/not-loaded"
    resources = {
        "https://schemas.example/root": {
            "$schema": JSON_SCHEMA_2020_12,
            "$ref": missing,
        }
    }

    with patch.object(
        urllib.request,
        "urlopen",
        side_effect=AssertionError("schema retrieval must remain offline"),
    ) as urlopen:
        result = validate_structural({}, schema, resources=resources)

    assert result.errors == [_reference_error(missing)]
    urlopen.assert_not_called()
