---
type: is
id: is-01kx6dmkfg4vcq8nfckm2e21zb
title: Replace portable regex backtracking with bounded linear engines
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - parity
  - regex
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx6mak81cn94pjt82awqdjqs
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T16:26:43.055Z
updated_at: 2026-07-10T18:36:56.112Z
closed_at: 2026-07-10T18:36:56.111Z
close_reason: Implemented bounded Thompson/lazy-DFA regex engines and aggregate work limits in both runtimes.
---
Replace native backtracking with bounded Thompson engines in both runtimes, normalize/index class ranges, cache compiled automata, enforce weighted per-match and aggregate validation work limits across patternProperties/key products, and prove allowed maximum scalar/schema shapes stay bounded without changing portable semantics.
