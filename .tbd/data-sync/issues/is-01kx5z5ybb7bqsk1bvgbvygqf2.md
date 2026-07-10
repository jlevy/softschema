---
type: is
id: is-01kx5z5ybb7bqsk1bvgbvygqf2
title: Document the TypeScript ArtifactValidationResult wrapper correctly
kind: bug
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - typescript
dependencies:
  - type: blocks
    target: is-01kx4w3nqewdhf1d3g0xgvj4ra
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:14:02.603Z
updated_at: 2026-07-10T12:50:40.756Z
closed_at: 2026-07-10T12:50:40.755Z
close_reason: Public API and TypeScript design docs correctly describe ArtifactValidationResult {ok, output} and failure handling; documentation tests pass.
---
Public API and TypeScript design docs imply validateArtifact returns legacy wire fields directly, but TypeScript returns {ok, output}. Update examples, result guidance, and parity tables to inspect result.output safely while explaining that output is the shared wire model.
