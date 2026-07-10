---
type: is
id: is-01kx64dj1kcrgqq3ngc3nrvwbx
title: Enforce TypeScript YAML node budgets during token iteration
kind: bug
status: closed
priority: 2
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - typescript
  - yaml
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T13:45:35.026Z
updated_at: 2026-07-10T14:15:12.708Z
closed_at: 2026-07-10T14:15:12.707Z
close_reason: YAML CST construction now enforces node and depth budgets incrementally.
---
TypeScript spreads the full YAML CST token iterator before applying the 100,000-node budget, allowing under-byte-limit inputs to allocate well beyond policy. Count and abort while iterating tokens without weakening syntax diagnostics or source mapping.

## Notes

TypeScript now drives Lexer and Parser incrementally, tracks explicit and implicit CST nodes plus depth during construction, preserves compact-flow syntax precedence with one-token bounded lookahead, and stops before test sentinels for scalar and implicit-map floods. Semantic node thresholds match Python across nested block/flow samples; conformance and full TypeScript gates pass.
