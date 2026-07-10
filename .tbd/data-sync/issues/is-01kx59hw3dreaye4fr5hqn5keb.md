---
type: is
id: is-01kx59hw3dreaye4fr5hqn5keb
title: Resolve nested JSON Schema resource identities and collisions
kind: bug
status: in_progress
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - json-schema
  - security
  - parity
dependencies:
  - type: blocks
    target: is-01kx4vfekaj195cy4tav9nrwgg
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T05:56:04.844Z
updated_at: 2026-07-10T05:56:22.664Z
---
Implement Draft 2020-12 base-aware traversal for nested $id resources in Python and TypeScript. Resolve relative nested IDs against the containing resource, reject an unbased relative nested ID, index embedded resources for fragment/reference lookup, detect duplicate resolved identities deterministically, preserve the offline no-retrieval boundary, and return identical stable schema_invalid identity records with shared vectors.
