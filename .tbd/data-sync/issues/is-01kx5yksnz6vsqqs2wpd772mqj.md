---
type: is
id: is-01kx5yksnz6vsqqs2wpd772mqj
title: Fix generated Copilot links for .github location
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - agents
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:04:07.999Z
updated_at: 2026-07-10T12:04:07.999Z
---
The generated .github/copilot-instructions.md copies repository-root-relative Markdown links from AGENTS.md, so links resolve under .github and break. Rewrite relative destinations for the adapter location and add a regression that every generated local link resolves.
