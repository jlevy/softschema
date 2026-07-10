---
type: is
id: is-01kx6dmm4pbyaq1t84cf5bswy8
title: Make wildcard segment matching linear
kind: bug
status: closed
priority: 2
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - performance
  - glob
  - parity
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T16:26:43.733Z
updated_at: 2026-07-10T18:36:57.946Z
closed_at: 2026-07-10T18:36:57.945Z
close_reason: Implemented bounded linear wildcard segment matching and invocation fuel in both runtimes.
---
Replace quadratic segment matching with the bounded exact prefix/interior/suffix algorithm, normalize class ranges, add shared per-segment and invocation-level glob pattern/token/work limits, qualify outer globstar complexity, and prove adversarial pattern/candidate products stay bounded in both runtimes.
