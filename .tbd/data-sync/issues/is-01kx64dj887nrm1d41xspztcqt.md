---
type: is
id: is-01kx64dj887nrm1d41xspztcqt
title: Use Unicode scalar ordering at every parity-visible schema traversal
kind: bug
status: closed
priority: 2
version: 5
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
updated_at: 2026-07-10T14:15:13.072Z
closed_at: 2026-07-10T14:15:13.071Z
close_reason: Parity-visible TypeScript traversals now use Unicode scalar ordering.
---
TypeScript still uses UTF-16 default sort order for pattern-property/schema-map traversal and structural-record comparison, so astral versus BMP keys can select different first failures than Python. Reuse the Unicode scalar comparator and add differential vectors.

## Notes

Applied compareUnicodeCodePoints to portable-pattern traversal, structural-record ordering, materialized object validation, resource registration, and portable sizing while preserving insertion order in returned values. Astral-versus-BMP failure-selection regressions, goldens, direct byte parity, and full TypeScript gates pass.
