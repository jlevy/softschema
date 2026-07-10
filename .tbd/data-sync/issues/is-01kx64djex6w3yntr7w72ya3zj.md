---
type: is
id: is-01kx64djex6w3yntr7w72ya3zj
title: Align multiline flow-mapping source spans across runtimes
kind: bug
status: closed
priority: 2
version: 5
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
updated_at: 2026-07-10T14:15:13.430Z
closed_at: 2026-07-10T14:15:13.429Z
close_reason: Multiline implicit flow-mapping spans now match across runtimes.
---
For multiline implicit flow mappings such as [a:\n], Python ends the pair span at the mapping-end event while TypeScript ends at the raw inline flow range. Define one boundary, add shared vectors, and make exact source locations match.

## Notes

Implicit flow-map spans now include trailing pair tokens through the mapping-end boundary. Added shared [a:\n] source-location vectors; Python and TypeScript focused tests, direct parity, and all-runtime conformance pass.
