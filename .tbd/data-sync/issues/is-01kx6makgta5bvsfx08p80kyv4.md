---
type: is
id: is-01kx6makgta5bvsfx08p80kyv4
title: Descriptor-bind remaining release-state JSON and hash reads
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - release
  - artifact
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
  - type: blocks
    target: is-01kx6p8vjpyjv6kvjb3r6zqc1s
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T18:23:35.449Z
updated_at: 2026-07-10T18:57:49.312Z
closed_at: 2026-07-10T18:36:58.851Z
close_reason: Descriptor-bound remaining release-state JSON and streaming-hash reads with race tests.
---
release_state still reads JSON and streams recovery/asset hashes through check-then-path-open helpers outside the authenticated regular-file boundary. Route JSON through explicit-budget regular bytes, descriptor-bind streaming hashes to lstat/open/fstat/path identity and stable metadata, detect replacement/growth including Windows second-pass semantics, and add adversarial tests.
