---
type: is
id: is-01kyx92expkcwgwm9srmwsr1m1
title: Normalize canonical Pydantic and Zod date schemas
kind: task
status: open
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-07-31-portable-yaml-timestamps.md
labels:
  - github-22
  - compiler-parity
dependencies:
  - type: blocks
    target: is-01kyx92qar1jne3qgxgk8hnn90
parent_id: is-01kyx90yh6vv5n0jdmhh5dar9n
created_at: 2026-07-31T23:45:08.021Z
updated_at: 2026-07-31T23:45:16.631Z
---
Add matching Pydantic date/datetime and Zod ISO date/date-time fields to the parity fixture. Use Zod toJSONSchema override hooks and public ISO schema classes to remove only each node's intrinsic ISO regex before canonicalization. Preserve authored z.string().regex constraints and regexes chained onto Zod ISO nodes. Regenerate the canonical sidecar and reviewed digest golden. Acceptance: both compilers emit type string plus format, preserve authored assertions, and produce the same schema_sha256.
