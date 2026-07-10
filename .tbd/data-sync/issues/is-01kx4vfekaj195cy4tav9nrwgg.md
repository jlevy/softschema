---
type: is
id: is-01kx4vfekaj195cy4tav9nrwgg
title: Separate the portable contract core from runtime and CLI adapters
kind: feature
status: closed
priority: 2
version: 10
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - architecture
  - python
  - typescript
dependencies:
  - type: blocks
    target: is-01kx4vfdwqtmk0tt9q9kznyhwq
  - type: blocks
    target: is-01kx4vfebyfym3whq7f3e3x0qs
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx5kpn97qaan54bsqh4yqtp8
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:50:05.417Z
updated_at: 2026-07-10T08:59:35.765Z
closed_at: 2026-07-10T07:55:24.873Z
close_reason: Implemented and verified in 30c41b0
---
Refactor incrementally toward a pure JSON-compatible contract core, runtime-specific YAML and model adapters, and thin filesystem and CLI adapters. Keep public entrypoints compatible and enforce that the TypeScript root library surface has no accidental Node-only dependencies.
