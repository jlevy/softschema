---
type: is
id: is-01m19xc7rq9gevsfm3851bv56j
title: "Docs: softschema-spec.md -- the CLI surface, the strict/checking rule, exit classes"
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies:
  - type: blocks
    target: is-01m19xcacbe2bz4n54qcjeh34c
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:16.727Z
updated_at: 2026-08-30T18:42:16.862Z
closed_at: 2026-08-30T18:42:16.862Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
docs/softschema-spec.md

State the surface (validate / repair / repair --dry-run / repair --check) and, as a normative rule, that strictness is a property of the command: validate is the consuming gate and refuses an unreadable artifact; repair is the producing loop and reports one. Give the exit classes explicitly (0 valid, 1 invalid or would-change under --check, 2 could not run).

This file is compared across implementations by cross-impl-diff.sh as 'docs spec', so the TypeScript resources must be rebuilt after editing or parity fails. Spec D1-D4.
