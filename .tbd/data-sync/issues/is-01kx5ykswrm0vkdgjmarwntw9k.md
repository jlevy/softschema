---
type: is
id: is-01kx5ykswrm0vkdgjmarwntw9k
title: Make trusted-publisher documentation reflect live verification state
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - release
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:04:08.214Z
updated_at: 2026-07-10T12:04:08.214Z
---
docs/publishing.md states that PyPI/npm trusted publishers are configured and bootstrap is complete even though the remediation plan records live authorization as unverified. Describe required settings separately from verified live state and remove unsupported completion claims.
