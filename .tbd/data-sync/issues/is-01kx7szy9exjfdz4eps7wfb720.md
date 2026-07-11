---
type: is
id: is-01kx7szy9exjfdz4eps7wfb720
title: Use one authored version string in softschema artifacts
kind: feature
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - artifact-format
  - simplicity
  - parity
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-11T05:21:51.917Z
updated_at: 2026-07-11T05:41:51.671Z
closed_at: 2026-07-11T05:41:51.670Z
close_reason: Removed the unmerged softschema.format discriminator across Python, TypeScript, conformance, release discovery, examples, docs, and agent skills; one closed metadata grammar now uses the contract ID as its only authored version string.
---
Remove the unmerged softschema.format discriminator so authored artifacts carry only the versioned contract ID. Use one closed metadata mapping grammar, allow extensions directly, update Python/TypeScript APIs and schemas, shared vectors, conformance claims, examples, docs, skills, and agent guidance, and keep Python/Node/Bun behavior aligned.
