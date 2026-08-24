---
type: is
id: is-01m0tep1j7p9216xena62th2zj
title: "S3: reject shared subschema object identities"
kind: bug
status: closed
priority: 2
version: 3
labels:
  - pr-review
  - enforcement
  - schema-graph
  - python
  - typescript
dependencies: []
parent_id: is-01m0tenataem0p1w6xmrynypvt
created_at: 2026-08-24T17:56:52.934Z
updated_at: 2026-08-24T18:48:47.447Z
closed_at: 2026-08-24T18:48:47.447Z
close_reason: "Implemented and verified in d0c12fa on PR #44; local full gate and all 18 GitHub checks pass."
resolution: null
duplicate_of: null
---
Reproduce graph metadata overwrite when one schema object instance appears at multiple positions, reject shared object identities with actionable deep-copy guidance, ensure the TypeScript content-addressed validator cache cannot bypass the identity check, and pin parity in both libraries.
