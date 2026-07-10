---
type: is
id: is-01kx5zjhz1jv8g28b6crwfknev
title: Bound standalone conformance consumer declared bytes
kind: bug
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - conformance
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:20:55.904Z
updated_at: 2026-07-10T12:50:40.937Z
closed_at: 2026-07-10T12:50:40.936Z
close_reason: Standalone conformance consumer rejects per-file declarations above 16 MiB and aggregate declarations above 64 MiB before hashing; focused and extracted-kit tests pass.
---
The standalone consumer accepts any nonnegative declared size and streams arbitrarily large or sparse files. Add strict per-file and aggregate declared-byte caps before hashing and adversarial tests, while preserving the standard-library-only extracted-kit verifier.
