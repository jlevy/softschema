---
type: is
id: is-01kx61q0qzxs2fmd6s611tzaex
title: Recheck immutable releases immediately before final publication
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - release
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:58:19.262Z
updated_at: 2026-07-10T13:09:03.076Z
closed_at: 2026-07-10T13:09:03.075Z
close_reason: Finalize job now rechecks immutable releases in the publication step immediately before gh release edit; workflow regression passes.
---
In the final release job, verify immutable releases remain enabled immediately before gh release edit changes the draft to published. Add a regression assertion that the pre-mutation check is present.
