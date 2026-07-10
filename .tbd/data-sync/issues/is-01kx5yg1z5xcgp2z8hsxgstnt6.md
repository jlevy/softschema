---
type: is
id: is-01kx5yg1z5xcgp2z8hsxgstnt6
title: Regenerate agent instruction shims after final AGENTS update
kind: bug
status: closed
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - agents
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:02:05.412Z
updated_at: 2026-07-10T12:02:20.587Z
closed_at: 2026-07-10T12:02:20.587Z
close_reason: Regenerated all deterministic agent adapters from AGENTS.md; sync_agent_instructions.py --check is green and the existing public-documentation regression covers drift.
---
The full Python gate detected that .github/copilot-instructions.md no longer matches the canonical AGENTS.md-derived shim. Regenerate the adapter, verify every target with --check, and retain a regression test.
