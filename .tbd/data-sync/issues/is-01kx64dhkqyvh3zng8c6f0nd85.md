---
type: is
id: is-01kx64dhkqyvh3zng8c6f0nd85
title: Bound SchemaView and compile drift file reads before allocation
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - python
  - typescript
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T13:45:34.582Z
updated_at: 2026-07-10T14:15:11.994Z
closed_at: 2026-07-10T14:15:11.993Z
close_reason: Bounded every remaining schema-file read before allocation in both runtimes.
---
SchemaView.load and compile check-only paths allocate complete schema files before max_resource_bytes enforcement, contradicting the bounded-reader contract. Route both runtimes through shared limit-plus-one readers and add adversarial tests proving early bounded rejection.

## Notes

Implemented shared Python/TypeScript limit-plus-one readers and routed SchemaView, compile drift, validation, CLI diagnostic, and resource loads through them. Focused bounded-read suites, built Node smoke, repository lint, full 662-test Python suite, and full 540-test TypeScript gate passed.
