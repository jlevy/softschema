---
type: is
id: is-01kx64dhkqyvh3zng8c6f0nd85
title: Bound SchemaView and compile drift file reads before allocation
kind: bug
status: closed
priority: 1
version: 11
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - python
  - typescript
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx6dmkpn710wq7wqsyvhxfzq
  - type: blocks
    target: is-01kx6dmkxknbjdge7z1kg1srpb
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T13:45:34.582Z
updated_at: 2026-07-10T18:36:55.660Z
closed_at: 2026-07-10T18:36:55.659Z
close_reason: Implemented descriptor-bound bounded schema readers in both runtimes with adversarial coverage.
---
SchemaView.load and compile check-only paths allocate complete schema files before max_resource_bytes enforcement, contradicting the bounded-reader contract. Route both runtimes through shared limit-plus-one readers and add adversarial tests proving early bounded rejection.

## Notes

All Python/TypeScript schema/artifact readers now canonicalize once, reject a non-regular target before open, open nonblocking/no-follow where supported, fstat regular and compare device/inode, loop bounded short reads, and use strict UTF-8 for compile drift. Parent/final file symlinks remain allowed through canonical targets per the public discovery contract; caller confinement remains explicit. Focused 12 Python + 4 Bun tests pass.
