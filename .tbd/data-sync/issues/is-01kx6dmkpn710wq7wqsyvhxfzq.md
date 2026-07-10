---
type: is
id: is-01kx6dmkpn710wq7wqsyvhxfzq
title: Validate final compiled sidecars after digest insertion
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - compiler
  - parity
  - security
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T16:26:43.284Z
updated_at: 2026-07-10T18:36:56.375Z
closed_at: 2026-07-10T18:36:56.373Z
close_reason: Implemented final sidecar revalidation, canonical drift comparison, and exact byte writes.
---
Both compilers enforce portable budgets before adding x-softschema.schema_sha256, Python check-only conflates JSON booleans and integers, and Windows text newline translation can exceed the checked byte limit. Revalidate final content, compare canonical JSON, write exact UTF-8 bytes, and add boundary regressions in both runtimes.
