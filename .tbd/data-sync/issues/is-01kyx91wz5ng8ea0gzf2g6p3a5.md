---
type: is
id: is-01kyx91wz5ng8ea0gzf2g6p3a5
title: Align TypeScript timestamp parsing and Date guard
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-31-portable-yaml-timestamps.md
labels:
  - github-22
  - typescript
dependencies:
  - type: blocks
    target: is-01kyx92qar1jne3qgxgk8hnn90
parent_id: is-01kyx90yh6vv5n0jdmhh5dar9n
created_at: 2026-07-31T23:44:49.636Z
updated_at: 2026-07-31T23:46:56.252Z
closed_at: 2026-07-31T23:46:56.252Z
close_reason: "Both runtime beads are implemented and their focused regressions pass: Python retains scoped constructor isolation and TypeScript retains string parsing while rejecting host-native Date metadata."
---
Remove the redundant plain-scalar timestamp rejection because the configured yaml parser already returns strings. Reject host-native JavaScript Date values in the internal portable metadata checker without changing validateValues semantics. Acceptance: shared decoding vectors pass unchanged, Zod ISO date/datetime semantic models distinguish valid and invalid strings, explicit tags still fail, and programmatic Date metadata returns the portable-domain error.

## Notes

TypeScript implementation and focused regression coverage are present; verifying parser behavior, semantic models, and the host-native Date guard before closure.
