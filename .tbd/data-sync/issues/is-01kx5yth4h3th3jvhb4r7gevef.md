---
type: is
id: is-01kx5yth4h3th3jvhb4r7gevef
title: Preserve the complete append-only Pages namespace during deployment
kind: feature
status: closed
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - architecture
  - conformance
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:07:48.625Z
updated_at: 2026-07-10T12:34:41.230Z
closed_at: 2026-07-10T12:34:41.229Z
close_reason: Added canonical complete Pages inventory, byte-verified live hydration, append-only union, immutable declared paths, and postdeploy verification of every retained/new file.
---
The current Pages artifact contains only schema/v1 and would replace future v2 or root content. Build and verify a complete append-only published namespace, with existing-version bytes retained exactly, before deployment.
