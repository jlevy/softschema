---
type: is
id: is-01kx64dj887nrm1d41xspztcqt
title: Use Unicode scalar ordering at every parity-visible schema traversal
kind: bug
status: closed
priority: 2
version: 9
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - typescript
  - schema
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T13:45:35.240Z
updated_at: 2026-07-10T18:36:57.045Z
closed_at: 2026-07-10T18:36:57.044Z
close_reason: Aligned all parity-visible traversal with Unicode scalar ordering.
---
TypeScript still uses UTF-16 default sort order for pattern-property/schema-map traversal and structural-record comparison, so astral versus BMP keys can select different first failures than Python. Reuse the Unicode scalar comparator and add differential vectors.

## Notes

Reopened: final parity review found raw Ajv preflight/cycle sorting plus a materialized-value first-failure mismatch between Python insertion traversal and TypeScript scalar traversal.
