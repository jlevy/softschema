---
type: is
id: is-01kx4vfe4k4c3631wxm1z6qnnw
title: Repair SchemaView and artifact-boundary edge cases
kind: bug
status: closed
priority: 2
version: 7
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - python
  - typescript
  - json-schema
dependencies:
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:50:04.946Z
updated_at: 2026-07-10T07:18:26.226Z
closed_at: 2026-07-10T07:18:26.225Z
close_reason: Implemented and verified in 99d5250
---
Preserve property-local annotations beside refs, unwrap only exact nullable-reference unions, represent genuine unions honestly, verify envelope and SchemaView code consumes the shared JSON-compatible mapping-key boundary without re-normalizing it, and make SchemaView mutability and exception contracts match their documentation.
