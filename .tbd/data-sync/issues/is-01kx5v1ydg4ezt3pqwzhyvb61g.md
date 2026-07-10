---
type: is
id: is-01kx5v1ydg4ezt3pqwzhyvb61g
title: Reject invalid Unicode scalars at every standalone JSON boundary
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - conformance
  - release
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx61kkznyp5d0pn9whrd28pr
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T11:01:57.295Z
updated_at: 2026-07-10T12:59:45.336Z
closed_at: 2026-07-10T11:51:34.369Z
close_reason: Standalone JSON boundaries reject duplicate/nonfinite/deep/huge/invalid-Unicode inputs deterministically in publication, consumers, adapters, runner, and release state.
---
Escaped unpaired UTF-16 surrogates survive Python json.loads and can later raise raw UnicodeEncodeError in publication, archive-consumer, adapter, runner, or frozen release-state serialization. Reject invalid Unicode scalar values in JSON keys and string values through bounded iterative validation, normalize deep/huge parser failures, and add hostile regression cases before refreshing authenticated manifests.
