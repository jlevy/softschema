---
type: is
id: is-01kx5yp94fbkctfd0hzaga4nvt
title: Reject TypeScript metadata-schema symlink escapes
kind: bug
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - typescript
dependencies:
  - type: blocks
    target: is-01kx4w3nqewdhf1d3g0xgvj4ra
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:05:29.358Z
updated_at: 2026-07-10T12:50:39.830Z
closed_at: 2026-07-10T12:50:39.829Z
close_reason: TypeScript metadata schema resolution now verifies realpath confinement while preserving missing-traversal parity; Python and TypeScript symlink-escape regressions plus full suites pass.
---
TypeScript metadata schema resolution checks lexical path containment before stat/read, so an in-root symlink can escape the document or cwd boundary. Resolve the real target before containment, preserve stable missing/input diagnostics, and add shared cross-runtime symlink-escape coverage.
