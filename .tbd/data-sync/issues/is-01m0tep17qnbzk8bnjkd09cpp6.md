---
type: is
id: is-01m0tep17qnbzk8bnjkd09cpp6
title: "S2: refuse overlapping structured property evaluators"
kind: bug
status: closed
priority: 1
version: 2
labels:
  - pr-review
  - enforcement
  - json-schema
  - python
  - typescript
dependencies: []
parent_id: is-01m0tenataem0p1w6xmrynypvt
created_at: 2026-08-24T17:56:52.598Z
updated_at: 2026-08-24T18:48:47.439Z
closed_at: 2026-08-24T18:48:47.439Z
close_reason: "Implemented and verified in d0c12fa on PR #44; local full gate and all 18 GitHub checks pass."
resolution: null
duplicate_of: null
---
Detect literal properties matched by patternProperties and conservatively overlapping structured pattern schemas when independent closure can over-narrow the same child value; refuse explicitly and pin both directions across runtimes.
