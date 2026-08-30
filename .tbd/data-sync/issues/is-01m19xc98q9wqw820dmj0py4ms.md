---
type: is
id: is-01m19xc98q9wqw820dmj0py4ms
title: "Docs: agent-repair.runbook.md -- every phase command"
kind: task
status: open
priority: 2
version: 3
labels: []
dependencies:
  - type: blocks
    target: is-01m19xcacbe2bz4n54qcjeh34c
  - type: blocks
    target: is-01m19xcyqz1ddyrpe6jbc0g4xa
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:18.263Z
updated_at: 2026-08-30T18:02:53.458Z
---
docs/agent-repair.runbook.md

Phases 1-3 shell out through the harness scripts (see the harness bead). Phase 4 invokes the CLI directly and names --check-repair in both regression cases. The Expected Results table and the prose describing what --check-repair asserts both need rewording for repair --check.

Keep the two regression cases intact; they pin real defects.
