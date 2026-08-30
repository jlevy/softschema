---
type: is
id: is-01m19xb9s5nxjaxmmwqzt5e1r0
title: "TypeScript: add loadArtifact, the strict consuming API"
kind: feature
status: closed
priority: 2
version: 4
labels: []
dependencies:
  - type: blocks
    target: is-01m19xbaj4bbdahk5vw24pp568
  - type: blocks
    target: is-01m19xc8gqjq2nksc03y981jez
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:46.021Z
updated_at: 2026-08-30T18:42:16.839Z
closed_at: 2026-08-30T18:42:16.839Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
packages/typescript/src/validate.ts plus the index.ts export. Mirror of the Python bead, same semantics and same thrown-error shape. Update the parity table in docs/softschema-typescript-design.md as part of the docs phase. Spec D5.
