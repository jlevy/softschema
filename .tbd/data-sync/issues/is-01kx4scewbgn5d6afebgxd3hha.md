---
type: is
id: is-01kx4scewbgn5d6afebgxd3hha
title: Harden CI and the pre-publish artifact boundary
kind: task
status: closed
priority: 1
version: 19
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
  - type: blocks
    target: is-01kx5ptpjcm7jjn4metv5k89tv
  - type: blocks
    target: is-01kx5rvwgnhq1db37qegdsyywp
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
child_order_hints:
  - is-01ksrzx0p7vnm70hqdzm4eqg9f
created_at: 2026-07-10T01:13:30.250Z
updated_at: 2026-07-10T11:40:39.351Z
closed_at: 2026-07-10T08:24:03.510Z
close_reason: Code-side artifact boundary implemented and verified in 6046517; live PR, publisher, and manual preflight evidence moved to ss-0rqn
---
After the draft release/doctor schemas exist, pin actions by SHA; introduce validated logical/build metadata; build and verify kit/wheel/sdist/npm bytes in correct non-self-referential order; test installed artifacts across the support matrix; and deliver a minimum protected tag-authorized PyPI/npm publisher plus CHANGELOG and 0.2.x safety note before the patch.

## Notes

Code-side implementation complete and locally verified: bounded compatible Python runtime ranges; dedicated locked Python and Bun vulnerability audit gates; npm consumer lock/control generated under npm 11.16.0 with a UTC cutoff 14 days old, strict registry, integrity, and checksum validation, and downstream npm ci --ignore-scripts; one checksummed wheel, sdist, and npm candidate built once and fanned out to the support matrix; full 0.2.2 safety-boundary and consolidated 0.3 migration disclosure. Evidence: 453 Python tests passed; repository lint passed including Ruff, basedpyright, codespell, formatting, and doc footers; 439 TypeScript tests passed with build, publint, and Bun audit green; pip-audit strict reported no known vulnerabilities after locking msgpack 1.2.1; real cold npm lock, audit, npm ci, and CLI smoke passed; local frozen build-once candidate wheel/sdist/npm smoke passed; uv lock check, Flowmark auto check, and git diff check passed. Keep in_progress until live-only gates pass: required PR contexts and Linux/macOS/Windows artifact matrix; manual publish workflow preflight; authenticated PyPI and npm trusted-publisher/environment verification. No registry publication, commit, push, or bead close performed.
