---
type: is
id: is-01kx5yksnz6vsqqs2wpd772mqj
title: Fix generated Copilot links for .github location
kind: bug
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - agents
dependencies:
  - type: blocks
    target: is-01kx4w3nqewdhf1d3g0xgvj4ra
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:04:07.999Z
updated_at: 2026-07-10T12:50:38.329Z
closed_at: 2026-07-10T12:50:38.328Z
close_reason: Generated Copilot links are rewritten for the .github location, every local target resolves, Makefile regeneration is durable after Flowmark, and shim drift/public-doc tests pass.
---
The generated .github/copilot-instructions.md copies repository-root-relative Markdown links from AGENTS.md, so links resolve under .github and break. Rewrite relative destinations for the adapter location and add a regression that every generated local link resolves.
