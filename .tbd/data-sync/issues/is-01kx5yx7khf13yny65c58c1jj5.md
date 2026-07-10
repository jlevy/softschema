---
type: is
id: is-01kx5yx7khf13yny65c58c1jj5
title: Persist release recovery state beyond Actions artifact retention
kind: bug
status: in_progress
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - security
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:09:17.168Z
updated_at: 2026-07-10T12:18:08.807Z
---
The protected release DAG depends exclusively on a seven-day Actions artifact. Delayed approvals, registry propagation, or half-release recovery after expiry cannot reuse the original frozen bytes, while draft assets omit the transferred state driver/full control closure. Persist a manifest-verified recovery bundle for the release lifetime or implement exact draft-asset reconstruction, and test the expired-artifact path.
