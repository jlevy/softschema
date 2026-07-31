---
type: is
id: is-01kyx91epgeesh0qp9ey64nzn6
title: Define shared timestamp decoding conformance
kind: task
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-31-portable-yaml-timestamps.md
labels:
  - github-22
  - parity
dependencies:
  - type: blocks
    target: is-01kyx91p86jxd9ftcdrm26f1xs
  - type: blocks
    target: is-01kyx91wz5ng8ea0gzf2g6p3a5
parent_id: is-01kyx90yh6vv5n0jdmhh5dar9n
created_at: 2026-07-31T23:44:35.023Z
updated_at: 2026-07-31T23:46:27.541Z
closed_at: 2026-07-31T23:46:27.534Z
close_reason: Shared timestamp vectors are implemented and revalidated in both adapters, including exact decoded-value assertions.
---
Update the shared portable-value vectors first. Cover valid and invalid calendar-shaped strings, quoted and unquoted dates, offset and space-separated datetimes, nanosecond lexical precision, and date-shaped mapping keys. Assert decoded values, not only success. Preserve explicit-tag rejection and all existing limits. Acceptance: both adapters consume the same vectors and the red tests demonstrate the old timestamp rejection before runtime changes.

## Notes

Implementation exists in tests/vectors/hardening.yaml and both adapter tests. Revalidating exact decoded values and shared behavior under the implement-beads shortcut.
