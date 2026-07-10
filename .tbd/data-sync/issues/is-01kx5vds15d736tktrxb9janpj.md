---
type: is
id: is-01kx5vds15d736tktrxb9janpj
title: Bound artifact and schema reads before allocation
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - io
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T11:08:24.996Z
updated_at: 2026-07-10T11:51:33.648Z
closed_at: 2026-07-10T11:51:33.647Z
close_reason: Artifact/schema reads are limit+1 bounded before allocation, decoding, and parsing in Python and TypeScript; adversarial tests pass.
---
Readers currently allocate whole untrusted files before enforcing byte limits. Replace with limit+1 bounded reads across Python and TypeScript, avoid diagnostic rereads, and prove oversized artifacts/schemas fail without full allocation.
