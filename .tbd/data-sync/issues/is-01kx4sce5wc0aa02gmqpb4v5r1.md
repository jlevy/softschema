---
type: is
id: is-01kx4sce5wc0aa02gmqpb4v5r1
title: Harden and standardize agent bootstrap instructions
kind: task
status: open
priority: 1
version: 11
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - agents
  - security
  - docs
dependencies:
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:29.531Z
updated_at: 2026-07-10T03:21:30.671Z
---
Make skill bootstrap capability-aware and deterministic: implement byte-compatible versioned doctor JSON in Python/TypeScript, verify PATH candidates, then try ecosystem-pinned uvx/npx/bunx candidates in fixed capable order. Omit allowed-tools, make the brief executable, and validate source/mirrors with deterministic discovery and dated activation checks.
