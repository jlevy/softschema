---
type: is
id: is-01kx6dmkxknbjdge7z1kg1srpb
title: Carry exact validated schema source maps into diagnostics
kind: bug
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - diagnostics
  - security
  - parity
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T16:26:43.506Z
updated_at: 2026-07-10T18:36:57.721Z
closed_at: 2026-07-10T18:36:57.720Z
close_reason: Carried identity-bound validated schema source maps into diagnostics without public wire changes.
---
Batch validation and schema diagnostics independently reread a schema, so an atomic replacement between reads can validate one identity and project locations from another. Bind ctime in file expectations and carry the exact parsed schema source map from structural validation to diagnostic projection without exposing provenance in public wire output.
