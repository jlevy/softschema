---
type: is
id: is-01kx5s2k0yz7q21ektrcfwkd75
title: Require release provenance postconditions before retry success
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - security
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
  - type: blocks
    target: is-01kx5zkegfyhhxb0j7s3gj1xbf
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T10:27:21.245Z
updated_at: 2026-07-10T13:10:39.051Z
closed_at: 2026-07-10T11:51:32.723Z
close_reason: Retry completion now requires the provenance/publisher postcondition; bounded-failure regressions pass.
---
The release-state retry loop can retain and return a complete registry decision after every required provenance postcondition fails. Retain a qualifying decision only after its postcondition succeeds; otherwise surface the final bounded failure. Add CLI coverage for complete PyPI bytes with Integrity/provenance absent or malformed through all attempts, and audit every caller using after_complete.
