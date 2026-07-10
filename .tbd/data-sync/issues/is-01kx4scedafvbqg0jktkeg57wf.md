---
type: is
id: is-01kx4scedafvbqg0jktkeg57wf
title: Make skill installation explicit-scope and non-clobbering
kind: bug
status: closed
priority: 1
version: 9
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - agents
  - cli
  - safety
dependencies:
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx6h7v99sya112z8xsj3ea20
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:29.769Z
updated_at: 2026-07-10T17:29:45.052Z
closed_at: 2026-07-10T06:40:47.964Z
close_reason: Implemented and verified in 0854bcc
---
Add explicit project/global scope and agent selectors; enforce canonical target/repository/home/root/symlink/worktree policy; protect unmanaged, newer, unknown, and locally modified managed files by prior digest; acquire sorted locks and revalidate; stage per-file atomic replacements with recoverable rollback; make dry-run mutation-free; and repair crash residue idempotently.
