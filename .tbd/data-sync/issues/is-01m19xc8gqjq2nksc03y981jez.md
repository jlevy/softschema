---
type: is
id: is-01m19xc8gqjq2nksc03y981jez
title: "Docs: both design docs -- the outcome/exit paragraph and the parity table"
kind: task
status: closed
priority: 2
version: 3
labels: []
dependencies:
  - type: blocks
    target: is-01m19xcacbe2bz4n54qcjeh34c
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:17.494Z
updated_at: 2026-08-30T18:42:16.865Z
closed_at: 2026-08-30T18:42:16.865Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
docs/softschema-python-design.md and docs/softschema-typescript-design.md both carry: 'The CLI reads once to infer document binding: readable results map to exits 0 or 1, while access and parse failures use its one-line stderr and exit-2 input boundary.'

That sentence describes the design this epic replaces, and it is the design doc's own statement of the flag-dependent behavior. Rewrite it to state the command-level rule instead.

Also: the Python doc's 'Alignment with python-cli-patterns' exit-code list, and the TypeScript doc's Python-TypeScript API parity table (add load_artifact/loadArtifact).
