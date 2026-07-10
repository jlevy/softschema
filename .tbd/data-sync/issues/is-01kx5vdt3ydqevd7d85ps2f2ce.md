---
type: is
id: is-01kx5vdt3ydqevd7d85ps2f2ce
title: Align empty YAML node source anchors
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - diagnostics
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T11:08:26.109Z
updated_at: 2026-07-10T11:51:33.468Z
closed_at: 2026-07-10T11:51:33.468Z
close_reason: Aligned implicit-null anchors across mapping/sequence/flow/comment/CRLF/EOF and CLI diagnostics in both runtimes.
---
Empty sequence-item source positions differ between Python and TypeScript. Define and implement shared anchoring for empty mapping values, sequence items, flow entries, CRLF, and EOF, with diagnostic vectors and CLI parity tests.
