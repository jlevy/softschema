---
type: is
id: is-01kx5zjhhw05jc2kngc335rk9w
title: Align remaining portable YAML node, scalar, and error parity
kind: bug
status: closed
priority: 1
version: 8
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - yaml
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:20:55.483Z
updated_at: 2026-07-10T18:36:55.432Z
closed_at: 2026-07-10T18:36:55.431Z
close_reason: Implemented shared YAML parity vectors and verified Python/Node/Bun parity.
---
Final differential review reproduced three TS/Python gaps: TS undercounts compact-flow mapping pairs inside sequences, normalizes plain 01/1. scalar spelling that Python preserves, and classifies malformed {1 as syntax while Python returns value_domain. Define the intended portable behavior in shared vectors and make Python/Node/Bun exact.

## Notes

Reopened differential closure covers suffix-only document-end policy, missing implicit flow-sequence keys, flow-opener comment separation, tag-before-alias/compact/depth ordering, %TAG handle expansion, and malformed explicit core-tag normalization.
