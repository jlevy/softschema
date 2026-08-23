---
type: is
id: is-01m0qvyh5593setechh24zbbn4
title: "PR42: Preserve offending field identity in structural errors"
kind: bug
status: in_progress
priority: 2
version: 5
spec_path: docs/project/reviews/review-2026-08-23-pr-42-schema-composition-design.md
labels:
  - pr-42
  - errors
  - parity
dependencies: []
parent_id: is-01m0qtv9aebdaw48z0f70bjf87
created_at: 2026-08-23T17:50:59.236Z
updated_at: 2026-08-23T18:56:51.050Z
---
The stable kind+code+path surface cannot distinguish two missing keys at one object path and undeclared-property records omit the offending key names. Required messages render the whole required list rather than the actual missing property.

## Notes

Implemented and verified in 9d69517 on codex/pr-42-schema-composition-fixes; final documentation, stacked PR, review disposition, and CI remain.
