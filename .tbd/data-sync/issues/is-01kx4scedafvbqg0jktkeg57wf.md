---
type: is
id: is-01kx4scedafvbqg0jktkeg57wf
title: Make skill installation explicit-scope and non-clobbering
kind: bug
status: open
priority: 1
version: 1
labels:
  - agents
  - cli
  - safety
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:29.769Z
updated_at: 2026-07-10T01:13:29.769Z
---
Project installation falls back to the current directory outside Git, so running in HOME writes global agent files, and existing skill files are overwritten without checking ownership or the advertised format guard. Require explicit project or global scope, refuse ambiguous locations, and protect unmanaged or newer-format files.
