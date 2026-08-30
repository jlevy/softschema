---
type: is
id: is-01m19xc84hfwfmk4a3xsfbw379
title: "Docs: softschema-guide.md -- the agent workflow section"
kind: task
status: closed
priority: 2
version: 3
labels: []
dependencies:
  - type: blocks
    target: is-01m19xcacbe2bz4n54qcjeh34c
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:17.105Z
updated_at: 2026-08-30T18:42:16.864Z
closed_at: 2026-08-30T18:42:16.864Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
docs/softschema-guide.md around line 842: step 5 'Validate and repair at each handoff' names 'softschema validate --repair' and '--check-repair'. Rewrite for the new commands and explain when an agent wants --dry-run versus --check.
