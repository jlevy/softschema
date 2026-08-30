---
type: is
id: is-01m19xahh31yvdk9arvvjt1qyp
title: "TypeScript: add the repair command, remove --repair/--check-repair from validate"
kind: feature
status: closed
priority: 1
version: 4
labels: []
dependencies:
  - type: blocks
    target: is-01m19xajct4hafm1daa780pfpj
  - type: blocks
    target: is-01m19xcybzz5zcr27y96q1vq5w
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:21.187Z
updated_at: 2026-08-30T18:42:16.828Z
closed_at: 2026-08-30T18:42:16.828Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
packages/typescript/src/cli.ts

Commander mirror of the Python surface. Identical flag names, identical help text, identical exit classes.

Remove the .option('--repair') and .option('--check-repair') from the validate command and the hand-rolled UsageError for their mutual exclusion. runRepairValidate becomes the repair command action.

Spec D1, D2, D4.
