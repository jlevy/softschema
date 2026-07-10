---
type: is
id: is-01kx4scewbgn5d6afebgxd3hha
title: Harden CI and the pre-publish artifact boundary
kind: task
status: open
priority: 1
version: 12
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - security
  - typescript
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
child_order_hints:
  - is-01ksrzx0p7vnm70hqdzm4eqg9f
created_at: 2026-07-10T01:13:30.250Z
updated_at: 2026-07-10T03:49:42.908Z
---
After the draft release/doctor schemas exist, pin actions by SHA; introduce validated logical/build metadata; build and verify kit/wheel/sdist/npm bytes in correct non-self-referential order; test installed artifacts across the support matrix; and deliver a minimum protected tag-authorized PyPI/npm publisher plus CHANGELOG and 0.2.x safety note before the patch.
