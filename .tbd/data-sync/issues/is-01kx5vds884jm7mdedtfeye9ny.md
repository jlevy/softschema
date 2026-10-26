---
type: is
id: is-01kx5vds884jm7mdedtfeye9ny
title: Make TypeScript source-map construction scale linearly
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/archive/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - performance
  - diagnostics
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T11:08:25.223Z
updated_at: 2026-10-26T03:52:22.314Z
closed_at: 2026-07-10T11:51:33.823Z
close_reason: SourceText now uses precomputed line/surrogate indexes with exact legacy-coordinate and no-rescan complexity tests.
---
SourceText.point and nextLinePoint rescan prefixes/line starts per YAML node, producing quadratic work within the supported node budget. Precompute searchable line/code-point indexes and add large deterministic performance/complexity coverage without changing locations.
