---
type: is
id: is-01kx5zkegfyhhxb0j7s3gj1xbf
title: Reject non-finite release retry delays
kind: bug
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - correctness
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:21:25.134Z
updated_at: 2026-07-10T12:41:13.913Z
closed_at: 2026-07-10T12:39:24.826Z
close_reason: Retry delay now requires a finite value in the bounded range before any operation or sleep; NaN, infinities, and negative values have regression tests.
---
The release retry helper accepts NaN delay values, which evade ordinary numeric comparisons and can reach sleep/backoff behavior. Require finite bounded delays at the boundary and add NaN/infinity/negative tests.
