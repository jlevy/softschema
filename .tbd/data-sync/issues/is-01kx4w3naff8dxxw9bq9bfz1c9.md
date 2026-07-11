---
type: is
id: is-01kx4w3naff8dxxw9bq9bfz1c9
title: Add artifact-format v1 and extension negotiation
kind: feature
status: closed
priority: 2
version: 10
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - spec
  - parity
  - compatibility
dependencies:
  - type: blocks
    target: is-01kx4vfekaj195cy4tav9nrwgg
  - type: blocks
    target: is-01kx4scdycksywq351ypme5nf8
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx7szy9exjfdz4eps7wfb720
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T02:01:07.662Z
updated_at: 2026-07-11T05:29:38.077Z
closed_at: 2026-07-10T07:18:26.053Z
close_reason: Implemented and verified in 99d5250
---
Add an explicit quoted softschema.format value 1 for newly authored artifacts while continuing to accept absent format as the legacy metadata grammar, add one namespaced extensions mapping, reject unknown versions and top-level keys, publish machine-readable metadata schemas for both grammars, and add Python/TypeScript compatibility and failure vectors. The format version is independent of package versions.
