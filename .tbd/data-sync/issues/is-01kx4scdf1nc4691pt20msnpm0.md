---
type: is
id: is-01kx4scdf1nc4691pt20msnpm0
title: Validate contract IDs at every API and CLI boundary
kind: bug
status: open
priority: 2
version: 1
labels:
  - parity
  - python
  - typescript
  - spec
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:28.801Z
updated_at: 2026-07-10T01:13:28.801Z
---
Contract ID grammar is enforced only in document metadata. Contract registries, explicit CLI overrides, and compilers accept malformed IDs and can emit invalid or inconsistent schema identifiers. Introduce one validated ContractId abstraction in each runtime and distinguish logical contract IDs from JSON Schema URI identifiers.
