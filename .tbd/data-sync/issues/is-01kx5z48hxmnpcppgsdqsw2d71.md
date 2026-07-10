---
type: is
id: is-01kx5z48hxmnpcppgsdqsw2d71
title: Verify GitHub latest-release pointer postconditions
kind: bug
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - correctness
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:13:07.516Z
updated_at: 2026-07-10T12:41:13.554Z
closed_at: 2026-07-10T12:39:24.464Z
close_reason: "Added bounded /releases/latest classification and final postconditions: stable tags must be exact latest and prereleases cannot displace stable latest; focused workflow and classifier tests pass."
---
The finalize workflow asks GitHub to mark stable releases latest, but the postcondition only rechecks release assets/state and never the /releases/latest pointer. Add bounded latest-endpoint classification so stable recovery verifies the exact latest tag and RCs cannot displace it.
