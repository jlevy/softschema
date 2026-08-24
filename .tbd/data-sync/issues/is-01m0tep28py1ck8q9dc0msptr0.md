---
type: is
id: is-01m0tep28py1ck8q9dc0msptr0
title: "S5: normalize TypeScript array-index paths"
kind: bug
status: closed
priority: 2
version: 2
labels:
  - pr-review
  - parity
  - typescript
  - validation-errors
dependencies: []
parent_id: is-01m0tenataem0p1w6xmrynypvt
created_at: 2026-08-24T17:56:53.654Z
updated_at: 2026-08-24T18:48:47.467Z
closed_at: 2026-08-24T18:48:47.467Z
close_reason: "Implemented and verified in d0c12fa on PR #44; local full gate and all 18 GitHub checks pass."
resolution: null
duplicate_of: null
---
Make TypeScript error paths use numeric array indexes like Python while preserving object keys that look numeric, and add a shared enforced array-element error vector.
