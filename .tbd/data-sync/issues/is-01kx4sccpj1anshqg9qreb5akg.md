---
type: is
id: is-01kx4sccpj1anshqg9qreb5akg
title: Prevent consumer repositories from shadowing bundled CLI resources
kind: bug
status: open
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - typescript
  - python
  - agents
dependencies:
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:28.016Z
updated_at: 2026-07-10T02:06:15.951Z
---
The TypeScript CLI walks arbitrary ancestors before bundled resources, and Python development resource detection can also match a consumer repository. A colliding skills/softschema/SKILL.md or docs path can replace trusted agent instructions. Prefer bundled resources in installed mode and require an exact source-checkout marker for development reads.
