---
type: is
id: is-01m0tep2k7kvpevkcg54v7pc0c
title: "S6: harden Python structural property recovery"
kind: bug
status: closed
priority: 3
version: 2
labels:
  - pr-review
  - python
  - validation-errors
  - testing
dependencies: []
parent_id: is-01m0tenataem0p1w6xmrynypvt
created_at: 2026-08-24T17:56:53.990Z
updated_at: 2026-08-24T18:48:47.474Z
closed_at: 2026-08-24T18:48:47.474Z
close_reason: "Implemented and verified in d0c12fa on PR #44; local full gate and all 18 GitHub checks pass."
resolution: null
duplicate_of: null
---
Derive missing required properties from structured validator data, retain unavoidable unevaluatedProperties parsing with explicit canary coverage for multiple and parenthesized keys, and preserve per-field parity.
