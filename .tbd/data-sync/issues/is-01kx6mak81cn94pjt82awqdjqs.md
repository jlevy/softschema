---
type: is
id: is-01kx6mak81cn94pjt82awqdjqs
title: Bound retained lazy-DFA subset membership
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - regex
  - parity
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T18:23:35.168Z
updated_at: 2026-07-10T18:36:58.623Z
closed_at: 2026-07-10T18:36:58.622Z
close_reason: Bound retained lazy-DFA subset membership per engine and across the persistent cache.
---
The bounded lazy-DFA engines cap states/transitions but can retain up to thousands of large NFA-state subsets per regex and across the 32-entry cache, allowing accepted patterns and inputs to amplify memory far beyond the advertised transition cap. Add shared per-engine and aggregate retained-membership budgets, stop or evict caching before insertion exceeds them, and prove bounded behavior in Python and TypeScript.
