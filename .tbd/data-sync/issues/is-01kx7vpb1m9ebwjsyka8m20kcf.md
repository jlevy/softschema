---
type: is
id: is-01kx7vpb1m9ebwjsyka8m20kcf
title: Simplify test architecture and use readable YAML goldens
kind: task
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - testing
  - maintainability
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
  - type: blocks
    target: is-01kx7y05kqvgmrf9zwxraf3cya
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-11T05:51:34.451Z
updated_at: 2026-07-11T06:31:57.712Z
closed_at: 2026-07-11T06:29:01.927Z
close_reason: Removed duplicate golden/parity execution and trivial tests, reduced the golden corpus, converted 59 human-reviewed expectation/vector/policy fixtures to strictly equivalent YAML, documented test-layer ownership, and passed the complete local and GitHub matrices.
---
Audit Python, TypeScript, shared golden, and conformance tests against tbd minimal-testing and golden-testing guidance. Remove duplicate/trivial coverage, simplify runners and fixtures, prefer YAML for human-reviewed golden data, retain JSON only where JSON wire behavior is itself under test, and validate coverage/CI.
