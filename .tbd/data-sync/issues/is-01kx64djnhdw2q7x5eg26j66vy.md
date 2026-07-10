---
type: is
id: is-01kx64djnhdw2q7x5eg26j66vy
title: Align release-manifest schema with runtime subject size policy
kind: bug
status: closed
priority: 2
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - security
  - conformance
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T13:45:35.664Z
updated_at: 2026-07-10T14:15:13.789Z
closed_at: 2026-07-10T14:15:13.788Z
close_reason: Release-manifest schema and runtime size policy now agree.
---
The release-manifest schema permits subject sizes above the runtime's 512 MiB per-subject ceiling and does not document the 1 GiB aggregate semantic limit. Add the exact schema maximum, document the aggregate rule, and test schema/runtime agreement.

## Notes

Release-manifest schema now caps subjects at 536870912 bytes and documents the 1073741824-byte aggregate semantic invariant enforced before reads. Schema/runtime max and max+1 tests, regenerated conformance integrity, 22-schema/25-case checks, and full suites pass.
