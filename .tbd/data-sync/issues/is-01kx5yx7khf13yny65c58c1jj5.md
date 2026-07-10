---
type: is
id: is-01kx5yx7khf13yny65c58c1jj5
title: Persist release recovery state beyond Actions artifact retention
kind: bug
status: closed
priority: 1
version: 9
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - security
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
  - type: blocks
    target: is-01kx61q0qz996v5p8kp0jt18g3
  - type: blocks
    target: is-01kx61rs7scpjsaxsmth92hefj
  - type: blocks
    target: is-01kx61tt02rykpj8fr1pc8y7xq
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:09:17.168Z
updated_at: 2026-07-10T13:00:26.753Z
closed_at: 2026-07-10T12:45:03.736Z
close_reason: Durable attested draft recovery plus 90-day initial transfer retention is implemented; every downstream job verifies and extracts the original frozen closure without rebuilding. Focused 36-test release-state suite, full release workflow tests, Ruff, and basedpyright pass.
---
The protected release DAG depends exclusively on a seven-day Actions artifact. Delayed approvals, registry propagation, or half-release recovery after expiry cannot reuse the original frozen bytes, while draft assets omit the transferred state driver/full control closure. Persist a manifest-verified recovery bundle for the release lifetime or implement exact draft-asset reconstruction, and test the expired-artifact path.
