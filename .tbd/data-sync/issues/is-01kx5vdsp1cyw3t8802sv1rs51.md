---
type: is
id: is-01kx5vdsp1cyw3t8802sv1rs51
title: Settle ambiguous compact-flow YAML semantics
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - yaml
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T11:08:25.664Z
updated_at: 2026-07-10T11:51:33.283Z
closed_at: 2026-07-10T11:51:33.282Z
close_reason: Settled compact-flow portability policy with shared accepted/rejected vectors and public conformance cases.
---
Python and TypeScript parse compact flow forms such as {a:} and [a:] into different values. Specify a shared portable policy, preferably rejecting ambiguous compact-flow colon forms, and add cross-runtime source/value/error vectors.
