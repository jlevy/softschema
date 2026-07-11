---
type: is
id: is-01kx7czj64w9bqs7kyd4yng4px
title: Resolve npm launcher portably in artifact smoke
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - ci
  - windows
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-11T01:34:28.035Z
updated_at: 2026-07-11T01:43:03.843Z
closed_at: 2026-07-11T01:39:12.053Z
close_reason: Resolved npm through PATH before strict non-shell execution; focused tests, full Python suite, lint, and real frozen artifact smoke pass.
---
Resolved npm through PATH before strict non-shell execution; focused tests, full Python suite, lint, real frozen artifact smoke, and Windows CI advanced past npm installation.
