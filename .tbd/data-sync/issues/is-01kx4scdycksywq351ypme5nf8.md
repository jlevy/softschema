---
type: is
id: is-01kx4scdycksywq351ypme5nf8
title: Expose pure-yaml validation through both CLIs
kind: feature
status: in_progress
priority: 2
version: 7
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - cli
  - parity
dependencies:
  - type: blocks
    target: is-01kx4vfebyfym3whq7f3e3x0qs
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:29.291Z
updated_at: 2026-07-10T07:19:31.336Z
---
Both libraries support the pure-yaml profile but both CLIs hardcode frontmatter-md, making a normative profile unreachable to normal users. Add a symmetric profile option or a carefully specified inference rule, a public example, and shared golden coverage.
