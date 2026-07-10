---
type: is
id: is-01kx4sce5wc0aa02gmqpb4v5r1
title: Harden and standardize agent bootstrap instructions
kind: task
status: open
priority: 1
version: 1
labels:
  - agents
  - security
  - docs
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:29.531Z
updated_at: 2026-07-10T01:13:29.531Z
---
The skill recommends unpinned latest network runners under a cool-off guarantee the package cannot enforce; npx may prompt; skill --brief uses an undefined runner variable; and allowed-tools is not strict Agent Skills syntax. Prefer local then pinned noninteractive fallbacks, make the brief self-contained, validate with skills-ref, and add activation and execution tests.
