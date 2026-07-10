---
type: is
id: is-01kx4scf42fe327rk346dhd0ym
title: Publish a versioned language-neutral conformance kit
kind: feature
status: in_progress
priority: 2
version: 15
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - spec
  - architecture
  - parity
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
  - type: blocks
    target: is-01kx5fvvr8jfgg5bf70vr9h5kj
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:30.497Z
updated_at: 2026-07-10T12:51:05.027Z
---
Complete the draft conformance foundation after every behavior and diagnostic bead settles; assign verified immutable HTTPS schema IDs; publish metadata/compiler-profile/legacy/diagnostic/vocabulary schemas, offline/compound bundle and evolution rules, supported-profile raw canonicalization cases, deterministic archive/manifest/digest, and standalone Python/Node/Bun execution.

## Notes

Code-side kit is complete and verified: 22 schemas, 25 ready artifact cases, 7 vector suites/77 vectors on Python, Node, and Bun; deterministic 135-file archive consumer passes. Pages now uses an append-only root index and reviewed promotion digest. Remaining gate is live Pages enablement/deploy/byte verification and committing the first promotion marker; API still returned 404 in the 2026-07-10 read-only audit.
