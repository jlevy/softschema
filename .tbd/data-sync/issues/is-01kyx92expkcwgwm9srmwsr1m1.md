---
type: is
id: is-01kyx92expkcwgwm9srmwsr1m1
title: Normalize canonical Pydantic and Zod date schemas
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-31-portable-yaml-timestamps.md
labels:
  - github-22
  - compiler-parity
dependencies:
  - type: blocks
    target: is-01kyx92qar1jne3qgxgk8hnn90
parent_id: is-01kyx90yh6vv5n0jdmhh5dar9n
created_at: 2026-07-31T23:45:08.021Z
updated_at: 2026-07-31T23:47:44.157Z
closed_at: 2026-07-31T23:47:44.156Z
close_reason: Focused Python and TypeScript compiler tests confirm canonical date/date-time schema and digest parity while preserving authored regex constraints.
---
Add matching Pydantic date/datetime and Zod ISO date/date-time fields to the parity fixture. Use Zod toJSONSchema override hooks and public ISO schema classes to remove only each node's intrinsic ISO regex before canonicalization. Preserve authored z.string().regex constraints and regexes chained onto Zod ISO nodes. Regenerate the canonical sidecar and reviewed digest golden. Acceptance: both compilers emit type string plus format, preserve authored assertions, and produce the same schema_sha256.

## Notes

Canonical sidecar, matching fixtures, targeted Zod override, authored-regex regression, and digest golden are implemented; verifying focused compiler parity.
