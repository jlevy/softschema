---
type: is
id: is-01kx62r2xrvqzg0518h4q1z4hg
title: Keep transient integration copies out of TypeScript coverage gates
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - typescript
  - testing
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T13:16:22.839Z
updated_at: 2026-07-10T13:18:38.083Z
closed_at: 2026-07-10T13:18:38.082Z
close_reason: Scoped transient integration copies out of Bun's per-file coverage gate and verified the complete TypeScript check passes.
---
Bun coverage currently instruments runtime-generated copies under temporary softschema-example/model-path directories. Per-file thresholding can make the full gate exit 1 despite 533 passing tests and 93.95%/97.95% aggregate coverage. Exclude only those transient integration copies while retaining coverage for package source, and add a configuration regression assertion.

## Notes

Bun coverage now excludes only generated dist bundles and runtime-created softschema-example/model-path copies; package src remains covered. Added a configuration regression that forbids broad src exclusion. Full bun run check is green: Biome, tsc, 534 tests/2069 assertions, 96.20% function and 97.84% line coverage.
