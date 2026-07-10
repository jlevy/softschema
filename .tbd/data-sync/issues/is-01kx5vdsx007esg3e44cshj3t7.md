---
type: is
id: is-01kx5vdsx007esg3e44cshj3t7
title: Make recursive discovery iterative and bounded
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - discovery
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx64dhv0p41vtygc1q9fdjbc
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T11:08:25.887Z
updated_at: 2026-07-10T13:45:52.549Z
closed_at: 2026-07-10T11:51:34.006Z
close_reason: Recursive discovery is iterative, identity-aware, and bounded to depth 64/100000 entries per operand with fail-closed partial-result behavior.
---
Recursive discovery can hit Python recursion depth or loop on directory identity cycles. Use iterative traversal in both runtimes, track directory identities, define shared depth/entry limits and stable input errors, and add deep/cycle parity tests.
