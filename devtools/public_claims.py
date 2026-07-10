#!/usr/bin/env python3
"""Check marked public claims against release and conformance metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[1]
CLAIMS_PATH = ROOT / "docs/public-claims.yaml"
CLAIMS_SCHEMA_PATH = ROOT / "conformance/schemas/public-claims.schema.json"
BEGIN = "<!-- BEGIN SOFTSCHEMA CLAIM {marker} -->"
END = "<!-- END SOFTSCHEMA CLAIM {marker} -->"


class ClaimError(ValueError):
    """A public claim is malformed, stale, or outside the repository."""


def load_yaml(path: Path) -> Any:
    """Load ordinary YAML as JSON-compatible data."""
    yaml = YAML(typ="safe")
    return yaml.load(path.read_text(encoding="utf-8"))


def resolve_pointer(document: Any, pointer: str) -> Any:
    """Resolve one RFC 6901 pointer without accepting URI-fragment syntax."""
    current = document
    if pointer == "":
        return current
    for encoded in pointer.removeprefix("/").split("/"):
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (IndexError, ValueError) as error:
                raise ClaimError(f"pointer does not resolve: {pointer}") from error
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            raise ClaimError(f"pointer does not resolve: {pointer}")
    return current


def scalar_values(value: Any) -> Iterator[str | int | float | bool | None]:
    """Yield every scalar leaf in a structured authoritative value."""
    if isinstance(value, dict):
        for child in value.values():
            yield from scalar_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from scalar_values(child)
    else:
        yield value


def contains_scalar(text: str, value: str | int | float | bool | None) -> bool:
    """Return whether a marked block contains one exact scalar spelling."""
    if value is None:
        spelling = "null"
    elif isinstance(value, bool):
        spelling = "true" if value else "false"
    else:
        spelling = str(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return re.search(rf"(?<![0-9]){re.escape(spelling)}(?![0-9])", text) is not None
    return spelling in text


def marked_text(path: Path, marker: str) -> str:
    """Extract one exact, nonduplicated generated-claim region."""
    text = path.read_text(encoding="utf-8")
    begin = BEGIN.format(marker=marker)
    end = END.format(marker=marker)
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ClaimError(f"{path.relative_to(ROOT)}: expected one marker pair for {marker}")
    start = text.index(begin) + len(begin)
    stop = text.index(end, start)
    return text[start:stop]


def check_claims() -> tuple[int, int]:
    """Validate the matrix and every target; return claim and target counts."""
    claims_document = load_yaml(CLAIMS_PATH)
    schema = json.loads(CLAIMS_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(claims_document), key=str)
    if errors:
        raise ClaimError(
            "public-claims schema failure: " + "; ".join(error.message for error in errors)
        )

    source_cache: dict[str, Any] = {}
    target_count = 0
    for claim_id, claim in claims_document["claims"].items():
        source_path = claim["source"]["path"]
        source = source_cache.get(source_path)
        if source is None:
            path = ROOT / source_path
            source = (
                json.loads(path.read_text(encoding="utf-8"))
                if path.suffix == ".json"
                else load_yaml(path)
            )
            source_cache[source_path] = source
        value = resolve_pointer(source, claim["source"]["pointer"])
        leaves = list(scalar_values(value))
        if not leaves:
            raise ClaimError(f"{claim_id}: authoritative value has no scalar leaves")
        for target in claim["targets"]:
            target_path = (ROOT / target["path"]).resolve()
            try:
                target_path.relative_to(ROOT.resolve())
            except ValueError as error:
                raise ClaimError(f"{claim_id}: target escapes repository") from error
            body = marked_text(target_path, target["marker"])
            missing = [leaf for leaf in leaves if not contains_scalar(body, leaf)]
            if missing:
                rendered = ", ".join(json.dumps(item, ensure_ascii=False) for item in missing)
                raise ClaimError(
                    f"{claim_id} -> {target['path']}#{target['marker']}: "
                    f"missing authoritative value(s) {rendered}"
                )
            target_count += 1
    return len(claims_document["claims"]), target_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check all claims (default)")
    parser.add_argument("--json", action="store_true", help="emit the summary as JSON")
    args = parser.parse_args(argv)
    try:
        claims, targets = check_claims()
    except (ClaimError, FileNotFoundError, json.JSONDecodeError) as error:
        print(f"public claims: {error}", file=sys.stderr)
        return 1
    summary = {"claims": claims, "ok": True, "targets": targets}
    print(
        json.dumps(summary, sort_keys=True)
        if args.json
        else f"public claims ok: {claims} claims, {targets} targets"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
