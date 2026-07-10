---
type: is
id: is-01kx4scdycksywq351ypme5nf8
title: Expose pure-yaml validation through both CLIs
kind: feature
status: closed
priority: 2
version: 9
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
updated_at: 2026-07-10T07:55:25.044Z
closed_at: 2026-07-10T07:55:25.043Z
close_reason: Implemented and verified in 30c41b0
---
Both libraries support the pure-yaml profile but both CLIs hardcode frontmatter-md, making a normative profile unreachable to normal users. Add a symmetric profile option or a carefully specified inference rule, a public example, and shared golden coverage.

## Notes

Implemented explicit --profile frontmatter-md|pure-yaml parity in Python and TypeScript CLIs with stable help/default/error behavior; added bundled copyable pure-YAML movie example, docs and agent-skill routing, safe installer upgrade digests, shared goldens for metadata-only, schema, semantic models, envelope/contract precedence, non-inference, malformed root, and value-domain errors, plus installed wheel/npm smoke coverage. Verified Python 448 tests and full lint, TypeScript 410 tests/check, goldens py 58/node 56/bun 58, byte-identical direct parity, conformance 16 schemas/23 ready/0 pending on Python+Node+Bun, Python build, npm build/publint, and installed-artifact smoke.
