---
type: is
id: is-01kx4sccpj1anshqg9qreb5akg
title: Prevent consumer repositories from shadowing bundled CLI resources
kind: bug
status: open
priority: 1
version: 1
labels:
  - security
  - typescript
  - python
  - agents
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:28.016Z
updated_at: 2026-07-10T01:13:28.016Z
---
The TypeScript CLI walks arbitrary ancestors before bundled resources, and Python development resource detection can also match a consumer repository. A colliding skills/softschema/SKILL.md or docs path can replace trusted agent instructions. Prefer bundled resources in installed mode and require an exact source-checkout marker for development reads.
