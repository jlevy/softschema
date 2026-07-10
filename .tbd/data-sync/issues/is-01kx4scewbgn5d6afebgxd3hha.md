---
type: is
id: is-01kx4scewbgn5d6afebgxd3hha
title: Harden reproducible package and release boundaries
kind: task
status: open
priority: 1
version: 1
labels:
  - release
  - security
  - typescript
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:30.250Z
updated_at: 2026-07-10T01:13:30.250Z
---
Pin GitHub Actions by full SHA in OIDC publish jobs, avoid unnecessary network installs after publish credentials are enabled, ensure npm pack builds fresh output, test installed wheel and tarball layouts, address caret-ranged CLI dependencies, and make partial PyPI/npm publication recovery explicit and idempotent.
