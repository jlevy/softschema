---
type: is
id: is-01kx5ykt9xyxf53p1g1dmfhhfz
title: Enforce exact bounded conformance archive tree inventory
kind: bug
status: open
priority: 2
version: 1
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - conformance
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:04:08.636Z
updated_at: 2026-07-10T12:04:08.636Z
---
conformance/consumer.py inventories only root/conformance and accepts undeclared root nodes or empty directories. Verify the exact allowed archive root and parent directory set with bounded traversal, and add adversarial regression cases.
