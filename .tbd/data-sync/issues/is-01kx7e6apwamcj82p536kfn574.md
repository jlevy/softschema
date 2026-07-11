---
type: is
id: is-01kx7e6apwamcj82p536kfn574
title: Use supported Node file-open flags on Windows
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
created_at: 2026-07-11T01:55:38.331Z
updated_at: 2026-07-11T02:17:26.748Z
closed_at: 2026-07-11T02:17:26.747Z
close_reason: Selected only Node-documented Windows open flags while retaining path/descriptor checks and POSIX hardening; focused and full TypeScript gates pass.
---
Node 22 Windows rejects POSIX O_NOFOLLOW/O_NONBLOCK open flags, normalizing exact artifacts as unreadable. Select only Node-documented Windows file-open flags there while retaining path/descriptor identity checks and POSIX no-follow/nonblocking flags; regression-test platform flag selection.
