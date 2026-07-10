---
type: is
id: is-01kx5zjhhw05jc2kngc335rk9w
title: Align remaining portable YAML node, scalar, and error parity
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - yaml
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:20:55.483Z
updated_at: 2026-07-10T12:41:12.649Z
closed_at: 2026-07-10T12:36:20.216Z
close_reason: Defined portable YAML spelling, implicit flow-pair node budgets, and syntax-precedence behavior in shared vectors; Python, Node, and Bun exact adapters pass all 32 cases.
---
Final differential review reproduced three TS/Python gaps: TS undercounts compact-flow mapping pairs inside sequences, normalizes plain 01/1. scalar spelling that Python preserves, and classifies malformed {1 as syntax while Python returns value_domain. Define the intended portable behavior in shared vectors and make Python/Node/Bun exact.
