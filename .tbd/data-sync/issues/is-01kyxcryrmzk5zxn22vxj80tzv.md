---
type: is
id: is-01kyxcryrmzk5zxn22vxj80tzv
title: Evaluate frontmatter-format v0.4.0 for softschema v0.4.0
kind: task
status: in_progress
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-31-softschema-v040-release.md
labels:
  - release-v0.4.0
dependencies: []
parent_id: is-01kyxcr75ap5xpcsm46p8edsq7
created_at: 2026-08-01T00:49:50.867Z
updated_at: 2026-08-01T01:31:44.713Z
---
Inspect the upcoming frontmatter-format v0.4.0 source and release plan, compare its API and dependency changes with softschema's writer-only usage, test the candidate against both packages and build artifacts, and make an explicit include-or-defer release decision with rationale.

## Notes

Verified published frontmatter-format v0.4.0 end to end: unannotated tag and GitHub release target merge commit 78e0dd4; tagged tree is identical to reviewed head f586298; PyPI wheel and sdist match reviewed candidate SHA-256 hashes 71d6b416c6b05242d934b6228d2386311f2f9216d4d1d47549e6cadf7963fe76 and dd7bc579b50e12a236c03427826a9af14fd2029e20dcae927e68f7440538e75a; sole runtime dependency remains ruamel-yaml>=0.18.10; Python 3.10-3.14 support retained; upstream lint/types and 51 tests pass; exact registry wheel and sdist install; timestamp and alias-free writer boundary probe passes. softschema now requires and locks frontmatter-format 0.4.0 with exact first-party exception 2026-08-01T01:26:20.316336Z in local config and every CI sync.
