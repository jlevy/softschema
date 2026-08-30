---
type: is
id: is-01m18sq9q4sxvxyvcyfygfd7cj
title: "PR #52 review F7: agent-repair runbook nits"
kind: bug
status: closed
priority: 3
version: 3
labels: []
dependencies: []
parent_id: is-01m18sp5xn5a5kpxza57ts9mbm
created_at: 2026-08-30T07:39:10.436Z
updated_at: 2026-08-30T07:55:15.875Z
closed_at: 2026-08-30T07:55:15.875Z
close_reason: "Fixed on claude/senior-engineering-review-h24e5m (b70010a, 12ef4ed). F2 turned out to be a live defect, not latent: --repair silently skipped any artifact whose closing fence was the file's last byte. Covered by 3 Python + 3 TypeScript cases, each verified to fail pre-fix, plus a golden journey on all three runtimes."
resolution: null
duplicate_of: null
---
docs/agent-repair.runbook.md:

1. Missing spaces around inline code in 'Things That Will Bite You': `yaml`immediately, span.`run_agents.py`anchors, leading`---`. Renders as run-together text.
2. Phase 4 invokes bare 'softschema', but nothing in the runbook puts it on PATH; every script in the harness uses 'uv run --frozen --no-config softschema'. A reader following Phase 4 literally either gets command-not-found or silently tests a different, globally installed build - the one outcome a regression check must not have.
3. Phase 4 copies prelim-scan-terms.schema.yaml into the temp dir, but the artifact it writes binds no schema (contract: t:M/v1, no schema: key). The cp is dead.
