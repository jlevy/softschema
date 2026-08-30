#!/usr/bin/env python3
"""Run each agent artifact through validate / repair --check / repair and classify.

Also checks the three conformance guarantees the spec states for repair:
byte-identical when nothing is needed, idempotent, and never writes a value its own
reader would reject.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
CLI = ["uv", "run", "--frozen", "--no-config", "softschema"]


def run(args: list[str]) -> tuple[int, dict | None, str]:
    p = subprocess.run([*CLI, *args], capture_output=True, text=True, cwd=HERE)
    try:
        return p.returncode, json.loads(p.stdout), p.stderr
    except json.JSONDecodeError:
        return p.returncode, None, (p.stdout + p.stderr)


def err_rows(res: dict | None) -> list[dict]:
    if not res:
        return []
    return res.get("structural", {}).get("errors", []) or []


# Failures about the document as a whole rather than about a field. They carry `kind` and
# `message` and neither `code` nor `path`, because there is no path into a document that
# would not parse. `_artifact_failure` and `unreadable_artifact_result` both emit this
# shape; scoring them against the field-repair surface would mark a precise diagnosis
# ("mapping values are not allowed here, line 22, column 12") as an unclear report.
DOCUMENT_LEVEL_KINDS = {
    "artifact_unreadable",
    "artifact_invalid_utf8",
    "yaml_parse_error",
    "no_frontmatter",
    "frontmatter_not_mapping",
    "yaml_not_mapping",
}


def actionable(e: dict) -> bool:
    """Whether a record tells the agent enough to act on it.

    Two shapes qualify. A field-level record must carry the spec's repair match surface:
    kind + code + path, plus property where the code names one. A document-level record
    qualifies on kind + message, which is all there is to say when the document did not
    parse.
    """
    if e.get("kind") in DOCUMENT_LEVEL_KINDS:
        return bool(e.get("message"))
    if not (e.get("kind") and e.get("code") and e.get("path") is not None):
        return False
    if e["code"] in {"undeclared_property", "missing_property"}:
        return bool(e.get("property"))
    return True


def document_level(errors: list[dict]) -> bool:
    return any(e.get("kind") in DOCUMENT_LEVEL_KINDS for e in errors)


def evaluate(src: Path, work: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "prelim-scan-terms.schema.yaml", work)
    target = work / src.name
    shutil.copy(src, target)
    rel = str(target.relative_to(HERE))
    original = target.read_bytes()

    rc0, before, raw0 = run(["validate", rel])
    rc_chk, _chk, _ = run(["repair", rel, "--check"])
    unwritten = target.read_bytes() == original

    rc1, after, raw1 = run(["repair", rel])
    once = target.read_bytes()
    _rc2, _after2, _ = run(["repair", rel])
    idempotent = target.read_bytes() == once

    repairs = (after or {}).get("repairs", []) or []
    errs = err_rows(after)

    if before and before.get("outcome") == "valid":
        verdict = "valid_as_is"
    elif after and after.get("outcome") == "valid":
        verdict = "repaired_to_valid"
    elif document_level(errs) and all(actionable(e) for e in errs):
        # Repair declined to guess at a document it could not parse -- a missing colon, an
        # unterminated fence -- and named the cause instead. That is the designed outcome,
        # not a shortfall: quoting cannot fix a line that is missing its key separator.
        verdict = "refused_with_cause"
    elif errs and all(actionable(e) for e in errs):
        verdict = "reported_cleanly"
    elif errs:
        verdict = "reported_unclear"
    else:
        verdict = "no_structural_verdict"

    return {
        "artifact": src.name,
        "verdict": verdict,
        "before_outcome": (before or {}).get("outcome", f"PARSE_FAIL rc={rc0} {raw0[:80]}"),
        "after_outcome": (after or {}).get("outcome", f"PARSE_FAIL rc={rc1} {raw1[:80]}"),
        "repairs": [{"code": r.get("code"), "path": r.get("path")} for r in repairs],
        "errors": [
            {
                "kind": e.get("kind"),
                "code": e.get("code"),
                "property": e.get("property"),
                "path": e.get("path"),
                "message": e.get("message", "")[:110],
            }
            for e in errs
        ],
        "repair_check_exit": rc_chk,
        "repair_check_left_file_unwritten": unwritten,
        "idempotent": idempotent,
        "byte_identical_when_noop": (original == once) if not repairs else None,
    }


def main() -> int:
    variant = sys.argv[1]
    srcdir = HERE / "runs" / variant
    work = HERE / "work" / variant
    shutil.rmtree(work, ignore_errors=True)
    results = [evaluate(p, work) for p in sorted(srcdir.glob("*.md"))]
    (HERE / f"results-{variant}.json").write_text(json.dumps(results, indent=2))
    for r in results:
        print(
            f"{r['artifact']:10} {r['verdict']:20} "
            f"{r['before_outcome']:9} -> {r['after_outcome']:9} "
            f"repairs={len(r['repairs'])} errors={len(r['errors'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
