---
type: is
id: is-01kx64djex6w3yntr7w72ya3zj
title: Align multiline flow-mapping source spans across runtimes
kind: bug
status: closed
priority: 2
version: 9
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - typescript
  - diagnostics
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T13:45:35.452Z
updated_at: 2026-07-10T18:36:57.277Z
closed_at: 2026-07-10T18:36:57.276Z
close_reason: Aligned multiline flow-mapping spans through shared source vectors.
---
For multiline implicit flow mappings such as [a:\n], Python ends the pair span at the mapping-end event while TypeScript ends at the raw inline flow range. Define one boundary, add shared vectors, and make exact source locations match.

## Notes

Reopened to include explicit ? flow-pair start boundaries as well as the settled multiline implicit-pair end boundary.
