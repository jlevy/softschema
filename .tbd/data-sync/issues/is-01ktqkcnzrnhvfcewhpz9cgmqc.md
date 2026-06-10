---
type: is
id: is-01ktqkcnzrnhvfcewhpz9cgmqc
title: Add softschema version reporting to both CLIs
kind: feature
status: open
priority: 2
version: 2
labels:
  - cli
  - parity
dependencies:
  - type: blocks
    target: is-01ktqkd1sgfem2nk4f4evp76sm
created_at: 2026-06-10T01:47:14.807Z
updated_at: 2026-06-10T01:48:20.500Z
---
Developer feedback: both implementations already know the installed package version for skill rendering, but users and agents cannot ask the CLI for it. Add `softschema --version` and keep Python and TypeScript behavior in parity, including golden or focused tests. Consider whether a `version` subcommand is also useful, but do not add a second surface unless it materially helps agents.
