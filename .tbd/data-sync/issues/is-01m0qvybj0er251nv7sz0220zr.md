---
type: is
id: is-01m0qvybj0er251nv7sz0220zr
title: "PR42: Apply reusable-definition closure at reference sites"
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/reviews/review-2026-08-23-pr-42-schema-composition-design.md
labels:
  - pr-42
  - json-schema
  - references
dependencies: []
parent_id: is-01m0qtv9aebdaw48z0f70bjf87
created_at: 2026-08-23T17:50:53.503Z
updated_at: 2026-08-23T19:16:28.278Z
closed_at: 2026-08-23T19:16:28.278Z
close_reason: "Resolved by checked graph enforcement in 9d69517, documentation reconciliation in 7f62269, final PR #42 disposition, and passing local plus GitHub CI validation on stacked PR #44."
---
Global per-definition closure is context-insensitive. A definition used in both standalone and composed contexts over-rejects the composed use, and a referring node with explicit unevaluatedProperties true cannot opt out because the target is already closed.

## Notes

Implemented and verified in 9d69517 on codex/pr-42-schema-composition-fixes; final documentation, stacked PR, review disposition, and CI remain.
