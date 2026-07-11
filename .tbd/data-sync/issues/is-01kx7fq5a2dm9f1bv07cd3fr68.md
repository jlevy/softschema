---
type: is
id: is-01kx7fq5a2dm9f1bv07cd3fr68
title: Handle legacy libuv Windows stat identity safely
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - ci
  - windows
  - security
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-11T02:22:18.433Z
updated_at: 2026-07-11T02:23:47.639Z
closed_at: 2026-07-11T02:23:47.638Z
close_reason: Version-gated only the unreliable path-to-descriptor ID comparison for libuv <1.51 on Windows, retaining all interface-local snapshots and size/read checks; primary-source upstream fixes linked and 593 TypeScript tests pass.
---
The minimum Node 22.12 runtime embeds libuv 1.49.1, predating upstream Windows fixes for FILE_STAT_BASIC_INFORMATION field order and volume serial handling. Path and descriptor dev/ino values can disagree for the same file. Version-gate only this cross-interface comparison while retaining path-to-path authorization, descriptor-to-descriptor stability, size checks, repeated Windows reads, and canonical-path checks; cover old/new libuv behavior.
