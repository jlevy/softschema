---
type: is
id: is-01kx5zjhz1jv8g28b6crwfknev
title: Bound standalone conformance consumer declared bytes
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - conformance
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:20:55.904Z
updated_at: 2026-07-10T12:20:55.904Z
---
The standalone consumer accepts any nonnegative declared size and streams arbitrarily large or sparse files. Add strict per-file and aggregate declared-byte caps before hashing and adversarial tests, while preserving the standard-library-only extracted-kit verifier.
