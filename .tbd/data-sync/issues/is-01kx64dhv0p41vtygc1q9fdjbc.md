---
type: is
id: is-01kx64dhv0p41vtygc1q9fdjbc
title: Replace recursive portable glob matching with bounded iteration
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - python
  - parity
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx6dmm4pbyaq1t84cf5bswy8
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T13:45:34.815Z
updated_at: 2026-07-10T16:29:09.665Z
closed_at: 2026-07-10T14:15:12.351Z
close_reason: Portable glob evaluation is stack-safe and parity-tested in both runtimes.
---
Python portable glob segment and globstar matching recurse with no pattern-length bound; valid adversarial patterns can escape the result boundary as RecursionError. Implement iterative dynamic programming and add shared long-pattern vectors that remain parity-safe.

## Notes

Replaced recursive segment and globstar matching with two-row iterative dynamic programming in Python and TypeScript. Shared 1,536-unit segment/path stress vectors pass in both runtimes; differential review covered prior semantics; full suites and type/lint gates passed.
