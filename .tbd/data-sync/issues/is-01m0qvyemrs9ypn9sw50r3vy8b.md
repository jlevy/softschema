---
type: is
id: is-01m0qvyemrs9ypn9sw50r3vy8b
title: "PR42: Prepare and validate the complete schema resource graph"
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/reviews/review-2026-08-23-pr-42-schema-composition-design.md
labels:
  - pr-42
  - json-schema
  - parity
dependencies: []
parent_id: is-01m0qtv9aebdaw48z0f70bjf87
created_at: 2026-08-23T17:50:56.662Z
updated_at: 2026-08-23T19:16:28.294Z
closed_at: 2026-08-23T19:16:28.294Z
close_reason: "Resolved by checked graph enforcement in 9d69517, documentation reconciliation in 7f62269, final PR #42 disposition, and passing local plus GitHub CI validation on stacked PR #44."
---
The overlay and portable-schema checks operate only on the root syntax tree. Anchors, nested definitions, dynamic references, and supplied external resources are not handled consistently; resources bypass enforced closure and portable regex checks.

## Notes

Implemented and verified in 9d69517 on codex/pr-42-schema-composition-fixes; final documentation, stacked PR, review disposition, and CI remain.
