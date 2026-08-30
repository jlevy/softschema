#!/usr/bin/env python3
"""Run each agent artifact through validate / --check-repair / --repair and classify.

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


def actionable(e: dict) -> bool:
    """The spec's field-repair match surface: kind + code + path (+ property)."""
    if not (e.get("kind") and e.get("code") and e.get("path") is not None):
        return False
    if e["code"] in {"undeclared_property", "missing_property"}:
        return bool(e.get("property"))
    return True


def evaluate(src: Path, work: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "prelim-scan-terms.schema.yaml", work)
    target = work / src.name
    shutil.copy(src, target)
    rel = str(target.relative_to(HERE))
    original = target.read_bytes()

    rc0, before, raw0 = run(["validate", rel])
    rc_chk, _chk, _ = run(["validate", rel, "--check-repair"])
    unwritten = target.read_bytes() == original

    rc1, after, raw1 = run(["validate", rel, "--repair"])
    once = target.read_bytes()
    _rc2, _after2, _ = run(["validate", rel, "--repair"])
    idempotent = target.read_bytes() == once

    repairs = (after or {}).get("repairs", []) or []
    errs = err_rows(after)

    if before and before.get("outcome") == "valid":
        verdict = "valid_as_is"
    elif after and after.get("outcome") == "valid":
        verdict = "repaired_to_valid"
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
                "code": e.get("code"),
                "property": e.get("property"),
                "path": e.get("path"),
                "message": e.get("message", "")[:110],
            }
            for e in errs
        ],
        "check_repair_exit": rc_chk,
        "check_repair_left_file_unwritten": unwritten,
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
