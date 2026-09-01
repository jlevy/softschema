---
type: is
id: is-01m19xcybzz5zcr27y96q1vq5w
title: "Manual harness: update the three agent-repair scripts"
kind: task
status: closed
priority: 2
version: 4
labels: []
dependencies:
  - type: blocks
    target: is-01m19xcyqz1ddyrpe6jbc0g4xa
  - type: blocks
    target: is-01m19xcz3ktm8yt7ajz1p5ww55
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:39.871Z
updated_at: 2026-08-30T18:42:16.874Z
closed_at: 2026-08-30T18:42:16.874Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
tests/manual/agent-repair/

evaluate.py runs both 'validate <p> --check-repair' and 'validate <p> --repair'; becomes 'repair <p> --check' and 'repair <p>'. The result field check_repair_left_file_unwritten should be renamed to match (it appears in results-*.json, which are gitignored, and in summarize.py).

summarize.py prints that field under 'conformance guarantees'.
feedback.py shells out through the same CLI list.

While here: evaluate.py classifies a correctly-refused unreadable artifact as no_structural_verdict, which reads like a harness failure rather than the right outcome. That is tracked separately as ss-p5sh; fold it in if convenient.
