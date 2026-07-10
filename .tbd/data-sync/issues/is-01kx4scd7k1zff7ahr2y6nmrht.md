---
type: is
id: is-01kx4scd7k1zff7ahr2y6nmrht
title: Define and enforce the cross-runtime JSON-compatible YAML value domain
kind: bug
status: closed
priority: 1
version: 15
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - python
  - typescript
  - spec
dependencies:
  - type: blocks
    target: is-01kx4scdps38egdehmsnnfqynp
  - type: blocks
    target: is-01kx4vfe4k4c3631wxm1z6qnnw
  - type: blocks
    target: is-01kx4vfekaj195cy4tav9nrwgg
  - type: blocks
    target: is-01kx4scdycksywq351ypme5nf8
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx4w3naff8dxxw9bq9bfz1c9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:28.562Z
updated_at: 2026-07-10T06:40:47.373Z
closed_at: 2026-07-10T06:40:47.372Z
close_reason: Implemented and verified in 0854bcc
---
Bound untrusted YAML before/during composition with shared byte, bundle, resource, node, depth, and scalar limits; size materialized inputs by compact canonical JSON; reject duplicate/non-string keys, tags, aliases, merges, cycles, timestamps, and unsafe values; define exact binary64/safe-integer/negative-zero behavior; and expose trusted library limit overrides.
