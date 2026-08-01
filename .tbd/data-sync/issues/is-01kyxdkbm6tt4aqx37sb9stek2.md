---
type: is
id: is-01kyxdkbm6tt4aqx37sb9stek2
title: Keep formatter checks isolated from user uv config
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/done/plan-2026-07-31-softschema-v040-release.md
labels:
  - release-v0.4.0
dependencies: []
parent_id: is-01kyxcr75ap5xpcsm46p8edsq7
created_at: 2026-08-01T01:04:15.998Z
updated_at: 2026-08-01T03:09:10.059Z
closed_at: 2026-08-01T01:05:25.459Z
close_reason: Formatter and generated-resource commands now ignore ambient uv config and use the frozen environment; direct run and pre-commit hook both leave uv.lock unchanged.
---
The Markdown pre-commit hook inherits user-level uv exclude-newer-package settings and rewrites the project lock with unrelated exceptions. Make formatting and generated-resource commands frozen and independent of ambient uv config; verify a commit leaves uv.lock unchanged.

## Notes

Reproduced during release pre-commit: ambient uv exclude-newer-package settings added unrelated 2100 exceptions to uv.lock. Makefile now uses --no-config for uvx and frozen --no-config for generated-resource commands; direct checksum test passes.
