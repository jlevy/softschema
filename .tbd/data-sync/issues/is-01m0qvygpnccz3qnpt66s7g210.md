---
type: is
id: is-01m0qvygpnccz3qnpt66s7g210
title: "PR42: Make status enforced a real API boundary guarantee"
kind: bug
status: in_progress
priority: 1
version: 5
spec_path: docs/project/reviews/review-2026-08-23-pr-42-schema-composition-design.md
labels:
  - pr-42
  - api
  - enforcement
dependencies: []
parent_id: is-01m0qtv9aebdaw48z0f70bjf87
created_at: 2026-08-23T17:50:58.768Z
updated_at: 2026-08-23T18:56:50.783Z
---
An enforced Contract with only a semantic model skips structural validation and can accept extras under Pydantic defaults. validate_values/validateValues also expose no status or strict-extras option, contradicting the documented status contract.

## Notes

Implemented and verified in 9d69517 on codex/pr-42-schema-composition-fixes; final documentation, stacked PR, review disposition, and CI remain.
