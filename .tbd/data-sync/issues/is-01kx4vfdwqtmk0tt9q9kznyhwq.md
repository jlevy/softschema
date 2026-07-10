---
type: is
id: is-01kx4vfdwqtmk0tt9q9kznyhwq
title: Align TypeScript runtime contracts, model loading, CLI exits, and wire types
kind: feature
status: open
priority: 2
version: 8
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - typescript
  - api
  - cli
  - parity
dependencies:
  - type: blocks
    target: is-01kx4vfebyfym3whq7f3e3x0qs
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
child_order_hints:
  - is-01ksrxy9by354mapnjhdgm7zpv
created_at: 2026-07-10T01:50:04.694Z
updated_at: 2026-07-10T07:36:54.541Z
---
Separate serializable contract descriptors from runtime Zod bindings without breaking 0.2 callers, document and enforce the Node versus Bun model-module policy, normalize Commander usage exits with Python, and replace Record<string, unknown> result surfaces with typed wire contracts.

## Notes

Architecture decision: softschema/core is transitively runtime-neutral, softschema/node is the explicit adapter, and the existing root remains a documented one-minor Node/Bun compatibility facade. Require transitive dependency and exact-export guards plus typed wire contracts, runtime binding separation, exit parity, and Windows-safe imports.
