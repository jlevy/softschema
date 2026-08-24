---
type: is
id: is-01m0tfbthsfev227r473tw68wz
title: "S8: refuse context-sensitive references whose targets are transformed"
kind: bug
status: closed
priority: 1
version: 3
labels:
  - pr-review
  - enforcement
  - json-schema
  - schema-graph
dependencies: []
parent_id: is-01m0tenataem0p1w6xmrynypvt
created_at: 2026-08-24T18:08:46.646Z
updated_at: 2026-08-24T18:48:47.487Z
closed_at: 2026-08-24T18:48:47.487Z
close_reason: "Implemented and verified in d0c12fa on PR #44; local full gate and all 18 GitHub checks pass."
resolution: null
duplicate_of: null
---
A ref under allOf, alternatives, conditionals, dependentSchemas, not, or contains—or beside validation siblings—can remain lexically unchanged while a reusable target receives nested inferred closure, changing intersection, selection, match, prohibition, or success semantics. Detect references whose evaluated targets would be transformed, refuse with a stable actionable reason, add paired semantic vectors, and document the pure-reference boundary.
