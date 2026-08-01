---
type: is
id: is-01kyxcryrmzk5zxn22vxj80tzv
title: Evaluate frontmatter-format v0.4.0 for softschema v0.4.0
kind: task
status: closed
priority: 1
version: 7
spec_path: docs/project/specs/active/plan-2026-07-31-softschema-v040-release.md
labels:
  - release-v0.4.0
dependencies: []
parent_id: is-01kyxcr75ap5xpcsm46p8edsq7
created_at: 2026-08-01T00:49:50.867Z
updated_at: 2026-08-01T02:07:20.579Z
closed_at: 2026-08-01T02:07:20.579Z
close_reason: "Completed on release commit e21f309: exact frontmatter-format 0.4.0 adoption, fast-uri 3.1.4 security hardening with approved exception, and full local release validation all passed."
---
Inspect the upcoming frontmatter-format v0.4.0 source and release plan, compare its API and dependency changes with softschema's writer-only usage, test the candidate against both packages and build artifacts, and make an explicit include-or-defer release decision with rationale.

## Notes

frontmatter-format adoption is implementation-complete: minimum and lock are 0.4.0, local environment and both exact softschema candidates install 0.4.0, the exact timestamp exception is present in pyproject and all three CI syncs, and full paired validation passed. Ready to close after the release commit.
