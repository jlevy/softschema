---
type: is
id: is-01m19xc98q9wqw820dmj0py4ms
title: "Docs: agent-repair.runbook.md -- every phase command"
kind: task
status: closed
priority: 2
version: 4
labels: []
dependencies:
  - type: blocks
    target: is-01m19xcacbe2bz4n54qcjeh34c
  - type: blocks
    target: is-01m19xcyqz1ddyrpe6jbc0g4xa
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:18.263Z
updated_at: 2026-08-30T18:42:16.869Z
closed_at: 2026-08-30T18:42:16.869Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
docs/agent-repair.runbook.md

Phases 1-3 shell out through the harness scripts (see the harness bead). Phase 4 invokes the CLI directly and names --check-repair in both regression cases. The Expected Results table and the prose describing what --check-repair asserts both need rewording for repair --check.

Keep the two regression cases intact; they pin real defects.
