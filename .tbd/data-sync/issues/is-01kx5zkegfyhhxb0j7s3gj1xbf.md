---
type: is
id: is-01kx5zkegfyhhxb0j7s3gj1xbf
title: Reject non-finite release retry delays
kind: bug
status: in_progress
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - correctness
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:21:25.134Z
updated_at: 2026-07-10T12:26:24.227Z
---
The release retry helper accepts NaN delay values, which evade ordinary numeric comparisons and can reach sleep/backoff behavior. Require finite bounded delays at the boundary and add NaN/infinity/negative tests.
