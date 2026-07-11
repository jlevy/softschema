---
type: is
id: is-01kx9qd9qmjfhmv9egzc34rwtj
title: "Step 9: Integrate the final paired API and CLI hard cut"
kind: task
status: open
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - api
  - cli
dependencies:
  - type: blocks
    target: is-01kx9qd9yk32j1nm52mmnrrffh
  - type: blocks
    target: is-01kx9qda5nktgj47m9c54mreg5
parent_id: is-01kx9n8xq83ng2r748pfrtd88e
created_at: 2026-07-11T23:15:12.755Z
updated_at: 2026-07-11T23:15:37.650Z
---
Integrate the accepted fixes behind one final idiomatic Python and TypeScript library surface and one coherent CLI contract. Remove replaced v0.2 exports, aliases, hidden legacy flags, byte-parity presentation assumptions, and alternate result projections. Preserve useful validate, compile, inspect, generate, docs, skill, doctor, frontmatter, pure-YAML, model, and schema workflows. Acceptance: final public exports and CLI help match the spec exactly and all stable error codes and exit classes are covered.
