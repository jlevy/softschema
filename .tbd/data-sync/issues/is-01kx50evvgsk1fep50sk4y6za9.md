---
type: is
id: is-01kx50evvgsk1fep50sk4y6za9
title: Make JSON Schema format semantics portable and annotation-only
kind: bug
status: open
priority: 2
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - json-schema
  - compatibility
dependencies:
  - type: blocks
    target: is-01kx4vfekaj195cy4tav9nrwgg
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T03:17:09.103Z
updated_at: 2026-07-10T03:21:31.080Z
---
For 0.3, make Draft 2020-12 format annotation-only in both runtimes: configure Ajv validateFormats false, prove known/unknown formats emit neither violations nor warnings, keep semantic model validation independent, document the compatibility change, add shared vectors, and reserve a future versioned assertion vocabulary.
