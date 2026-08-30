---
type: is
id: is-01m19xcybzz5zcr27y96q1vq5w
title: "Manual harness: update the three agent-repair scripts"
kind: task
status: open
priority: 2
version: 3
labels: []
dependencies:
  - type: blocks
    target: is-01m19xcyqz1ddyrpe6jbc0g4xa
  - type: blocks
    target: is-01m19xcz3ktm8yt7ajz1p5ww55
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:39.871Z
updated_at: 2026-08-30T18:02:53.797Z
---
tests/manual/agent-repair/

evaluate.py runs both 'validate <p> --check-repair' and 'validate <p> --repair'; becomes 'repair <p> --check' and 'repair <p>'. The result field check_repair_left_file_unwritten should be renamed to match (it appears in results-*.json, which are gitignored, and in summarize.py).

summarize.py prints that field under 'conformance guarantees'.
feedback.py shells out through the same CLI list.

While here: evaluate.py classifies a correctly-refused unreadable artifact as no_structural_verdict, which reads like a harness failure rather than the right outcome. That is tracked separately as ss-p5sh; fold it in if convenient.
