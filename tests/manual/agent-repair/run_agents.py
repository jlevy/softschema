#!/usr/bin/env python3
"""Drive Gemini over the prelim-scan-terms form and save whatever it writes.

The agent sees the runbook and the template only -- never the JSON Schema. Field-name
and value drift therefore arise the way they do in the real pipeline.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

TICKERS = [
    ("NKE", "Nike"),
    ("AAPL", "Apple"),
    ("SBUX", "Starbucks"),
    ("CROX", "Crocs"),
    ("ULTA", "Ulta Beauty"),
    ("TSCO", "Tractor Supply"),
    ("WING", "Wingstop"),
    ("DECK", "Deckers Outdoor"),
    ("FIVE", "Five Below"),
    ("PLNT", "Planet Fitness"),
    ("EXPO", "Exponent Inc"),
    ("AAON", "AAON Inc"),
]

PROMPT_TEMPLATED = """{runbook}

---

Here is the template to fill in:

```markdown
{template}
```

---

Fill in the form for ticker {ticker} ({company}). Today is 2026-08-30.
"""

# Prose mode: no field list, no template body. The agent derives the field names from
# the runbook prose, the way a stage whose shape is described rather than templated does.
PROMPT_PROSE = """{runbook}

---

Write the document as Markdown with YAML frontmatter. It must begin with a `---` line,
carry the metadata, and close the frontmatter with another `---` line before the body.
The frontmatter must open with exactly this block, then carry the form values under the
`prelim_scan_terms:` key, per the runbook above:

    ---
    softschema:
      contract: trading.prelim_scan:PrelimScanTerms/v1
      schema: prelim-scan-terms.schema.yaml
      envelope: prelim_scan_terms
      status: enforced
    prelim_scan_terms:
      ...the form values...
    ---

After the closing `---`, add a `# {ticker} - Prelim Scan Terms` heading and a Notes
paragraph.

---

Fill in the form for ticker {ticker} ({company}). Today is 2026-08-30.
"""


def call(model: str, budget: int, prompt: str) -> str:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"thinkingConfig": {"thinkingBudget": budget}, "temperature": 1.0},
    }
    req = urllib.request.Request(
        API.format(model=model, key=os.environ["GOOGLE_API_KEY"]),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    parts = d["candidates"][0]["content"].get("parts", [])
    # With a thinking budget the first part can be a thought summary; keep only answer parts.
    return "\n".join(x.get("text", "") for x in parts if not x.get("thought"))


def extract(text: str) -> str:
    """Pull the artifact out of the reply.

    The artifact always opens with a `---` frontmatter fence, so anchor on that rather
    than on code fences: a thinking model often nests ```markdown around ```yaml, and a
    fence-only regex captures the empty span between the two openers.
    """
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip() == "---"), None)
    if start is None:
        m = re.search(r"```(?:markdown|md|yaml)?\s*\n(.*?)```", text, re.S)
        return (m.group(1) if m else text).strip() + "\n"
    body = [ln for ln in lines[start:] if not ln.strip().startswith("```")]
    return "\n".join(body).strip() + "\n"


def main() -> int:
    model, budget, variant = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    mode = sys.argv[4] if len(sys.argv) > 4 else "templated"
    runbook = (HERE / "form-runbook.md").read_text()
    template = (HERE / "form-template.md").read_text()
    outdir = HERE / "runs" / variant
    outdir.mkdir(parents=True, exist_ok=True)

    def one(tc: tuple[str, str]) -> str:
        ticker, company = tc
        tpl = PROMPT_PROSE if mode == "prose" else PROMPT_TEMPLATED
        prompt = tpl.format(runbook=runbook, template=template, ticker=ticker, company=company)
        try:
            raw = call(model, budget, prompt)
        except Exception as e:
            return f"{ticker}: CALL FAILED {e}"
        (outdir / f"{ticker}.md").write_text(extract(raw))
        return f"{ticker}: ok"

    with ThreadPoolExecutor(max_workers=6) as pool:
        for line in pool.map(one, TICKERS):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
