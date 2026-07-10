---
type: is
id: is-01kx4scdps38egdehmsnnfqynp
title: Make canonicalization and enforced overlays semantics-preserving
kind: bug
status: in_progress
priority: 1
version: 9
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - json-schema
dependencies:
  - type: blocks
    target: is-01kx4vfe4k4c3631wxm1z6qnnw
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx4vfekaj195cy4tav9nrwgg
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:29.048Z
updated_at: 2026-07-10T05:24:00.779Z
---
Make nullable rewriting and recursive schema traversal semantics-preserving within the documented compiler profile. Normalize additionalProperties and unevaluatedProperties consistently, traverse every supported Draft 2020-12 applicator, and return stable enforcement_unsupported instead of partially closing compositions.
