---
type: is
id: is-01kx5ykt9xyxf53p1g1dmfhhfz
title: Enforce exact bounded conformance archive tree inventory
kind: bug
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - conformance
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx5zjhz1jv8g28b6crwfknev
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:04:08.636Z
updated_at: 2026-07-10T13:10:39.907Z
closed_at: 2026-07-10T12:50:38.908Z
close_reason: Standalone kit verification now enforces the exact root/file/directory inventory with bounded streaming traversal and rejects root extras, empty directories, symlinks, and special nodes; focused and full tests pass.
---
conformance/consumer.py inventories only root/conformance and accepts undeclared root nodes or empty directories. Verify the exact allowed archive root and parent directory set with bounded traversal, and add adversarial regression cases.
