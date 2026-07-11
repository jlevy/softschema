---
type: is
id: is-01kx7dqzt6q0sh4n4pxfjx9qj2
title: Compare bounded reads through descriptor snapshots on Windows
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - ci
  - windows
  - security
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
  - type: blocks
    target: is-01kx7e6apwamcj82p536kfn574
  - type: blocks
    target: is-01kx7fq5a2dm9f1bv07cd3fr68
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-11T01:47:48.421Z
updated_at: 2026-07-11T02:22:59.583Z
closed_at: 2026-07-11T01:51:42.874Z
close_reason: Separated path authorization from descriptor stability in Python and TypeScript bounded readers; regression, full Python/TypeScript suites, lint/typecheck, and real frozen artifact smoke pass.
---
Python bounded reads compare Windows path-stat timestamps with descriptor-stat timestamps, whose representations can differ, so exact installed schemas are misreported as syntax failures. Keep path-stat admission/authorization comparisons path-to-path, use the opened descriptor snapshot as the read/final stability baseline, and regression-test path/descriptor timestamp skew without weakening identity or mutation checks.
