---
type: is
id: is-01kx4wbvn70kp1txr9vfec8v64
title: Normalize artifact parse and access failures across single and batch validation
kind: bug
status: closed
priority: 1
version: 9
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - cli
  - errors
dependencies:
  - type: blocks
    target: is-01kx4scd7k1zff7ahr2y6nmrht
  - type: blocks
    target: is-01kx4vfebyfym3whq7f3e3x0qs
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T02:05:36.294Z
updated_at: 2026-07-10T06:40:48.162Z
closed_at: 2026-07-10T06:40:48.162Z
close_reason: Implemented and verified in 0854bcc
---
Return discriminated parse_error results with stable frontmatter, syntax, and root reasons for readable malformed Markdown/pure YAML; preserve exit 2 for not_found, unreadable, and directory-without-recursive inputs; define mixed-batch precedence; and leave value_domain reserved for ss-l41u.
