---
type: is
id: is-01kx64djwdf2rppmq5gv8qfs1t
title: Qualify legacy single-file JSON output compatibility
kind: task
status: closed
priority: 3
version: 8
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - compatibility
dependencies:
  - type: blocks
    target: is-01kx4w3nqewdhf1d3g0xgvj4ra
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T13:45:35.884Z
updated_at: 2026-07-10T18:36:58.396Z
closed_at: 2026-07-10T18:36:58.395Z
close_reason: Qualified legacy single-file JSON compatibility in spec, skill, guide, and golden output.
---
The spec says every explicit one-file JSON request uses the legacy result, while unreadable symlinks, FIFOs, and other discovery-input failures intentionally use diagnostic aggregates. Qualify the claim to readable regular files and document discovery-input behavior.

## Notes

Reopened after final audit found stale plan, migration, and skill wording that overstates legacy one-file JSON compatibility.
