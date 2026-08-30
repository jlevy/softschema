#!/usr/bin/env python3
"""Round 2: hand the agent back exactly what softschema reported, and re-validate.

This is the loop the feature exists to enable: the producing agent runs the same check
its consumer will run, and acts on the answer before it exits.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
CLI = ["uv", "run", "--frozen", "--no-config", "softschema"]

# Every record the validator emitted goes back to the agent. An earlier run capped this
# at 60 and scored 9 of 12; the three failures were exactly the records withheld. Raise
# it rather than lower it.
RECORD_CAP = 500
API = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}"

FIX = """You wrote this artifact:

```markdown
{doc}
```

A schema validator rejected it. These are the exact records it returned:

```json
{errors}
```

Each record names the JSON path, the offending or missing property, and why.
Fix the document so it validates. Change only what the records call out.
Return the corrected document in a single fenced `markdown` block.
"""


def sh(args, cwd):
    p = subprocess.run([*CLI, *args], capture_output=True, text=True, cwd=cwd)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return None


def call(prompt):
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"thinkingConfig": {"thinkingBudget": 0}, "temperature": 1.0},
    }
    req = urllib.request.Request(
        API.format(m="gemini-2.5-flash", k=os.environ["GOOGLE_API_KEY"]),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)["candidates"][0]["content"]["parts"][0]["text"]


def extract(t):
    import re

    m = re.search(r"```(?:markdown|md)?\s*\n(.*?)```", t, re.S)
    return (m.group(1) if m else t).strip() + "\n"


def main():
    variant = sys.argv[1]
    work = HERE / "work" / variant  # already repaired in place
    out = HERE / "work" / f"{variant}-round2"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    shutil.copy(HERE / "prelim-scan-terms.schema.yaml", out)

    todo = []
    for p in sorted(work.glob("*.md")):
        res = sh(["validate", p.name, "--check-repair"], work)
        if res and res.get("outcome") != "valid":
            todo.append((p, res["structural"]["errors"]))

    def fix(item):
        p, errs = item
        slim = [
            {k: e.get(k) for k in ("kind", "code", "path", "property", "message")} for e in errs
        ][:RECORD_CAP]
        try:
            new = extract(call(FIX.format(doc=p.read_text(), errors=json.dumps(slim, indent=2))))
        except Exception as e:
            return f"{p.name}: CALL FAILED {e}"
        (out / p.name).write_text(new)
        after = sh(["validate", p.name, "--repair"], out)
        oc = (after or {}).get("outcome", "PARSE_FAIL")
        n = len((after or {}).get("structural", {}).get("errors", []))
        return f"  {p.name:10} round2 -> {oc:9} (errors {len(errs)} -> {n})"

    print(f"{len(todo)} artifacts still invalid after --repair; sending reports back\n")
    with ThreadPoolExecutor(max_workers=6) as pool:
        for line in pool.map(fix, todo):
            print(line)


if __name__ == "__main__":
    main()
