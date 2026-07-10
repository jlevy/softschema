---
type: is
id: is-01kx4sce5wc0aa02gmqpb4v5r1
title: Harden and standardize agent bootstrap instructions
kind: task
status: closed
priority: 1
version: 14
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - agents
  - security
  - docs
dependencies:
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx5z0gv8d14ef9gd7exwpyg2
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:29.531Z
updated_at: 2026-07-10T13:10:41.613Z
closed_at: 2026-07-10T06:40:47.771Z
close_reason: Implemented and verified in 0854bcc
---
Make skill bootstrap capability-aware and deterministic: implement byte-compatible versioned doctor JSON in Python/TypeScript, verify PATH candidates, then try ecosystem-pinned uvx/npx/bunx candidates in fixed capable order. Omit allowed-tools, make the brief executable, and validate source/mirrors with deterministic discovery and dated activation checks.
