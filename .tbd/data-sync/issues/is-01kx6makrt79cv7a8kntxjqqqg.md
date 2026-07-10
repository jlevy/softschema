---
type: is
id: is-01kx6makrt79cv7a8kntxjqqqg
title: Correct release review source-checkout claim
kind: bug
status: closed
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - release
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T18:23:35.705Z
updated_at: 2026-07-10T18:36:59.080Z
closed_at: 2026-07-10T18:36:59.079Z
close_reason: Corrected release review to describe the exact-checkout trusted verifier accurately.
---
The release boundary review says registry jobs do not check out source, while the hardened workflow checks out the exact preflight commit solely to execute the trusted verifier. Align the review with the workflow and clarify that jobs do not resolve dependencies, rebuild, or execute candidate lifecycle scripts.
