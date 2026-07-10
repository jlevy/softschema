---
type: is
id: is-01kx4scewbgn5d6afebgxd3hha
title: Harden CI and the pre-publish artifact boundary
kind: task
status: in_progress
priority: 1
version: 15
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
  - type: blocks
    target: is-01kx5fvvr8jfgg5bf70vr9h5kj
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
child_order_hints:
  - is-01ksrzx0p7vnm70hqdzm4eqg9f
created_at: 2026-07-10T01:13:30.250Z
updated_at: 2026-07-10T07:46:36.432Z
---
After the draft release/doctor schemas exist, pin actions by SHA; introduce validated logical/build metadata; build and verify kit/wheel/sdist/npm bytes in correct non-self-referential order; test installed artifacts across the support matrix; and deliver a minimum protected tag-authorized PyPI/npm publisher plus CHANGELOG and 0.2.x safety note before the patch.

## Notes

Closure gates added by the July preflight: bounded compatible Python runtime ranges; locked audits in CI; npm consumer resolution generated with pinned npm and a 14-day --before cutoff, transferred with exact package-lock/control/checksums, validated, and installed via npm ci; one build fanned out to the platform smoke matrix; complete safety/migration disclosure; successful PR contexts and manual preflight; authenticated PyPI/npm publisher/environment verification. Record the consolidated 0.3 release decision rather than implying an interim 0.2.3 shipped.
