---
type: is
id: is-01kx4w3nh1qz49ffey0dgewxp7
title: Make dual-registry releases idempotent and verify published artifacts
kind: task
status: open
priority: 1
version: 8
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - security
  - packaging
dependencies:
  - type: blocks
    target: is-01kx4w3nqewdhf1d3g0xgvj4ra
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T02:01:07.872Z
updated_at: 2026-07-10T11:52:50.923Z
---
Freeze the full 0.3 release candidate, then publish external-manifest-verified bytes through a draft-assets/attestation → PyPI+npm → final-release DAG. Implement ecosystem version/pin/prerelease mapping, registry-specific state/recovery, SPDX SBOM and current GitHub attestation verification, npm trusted-publisher recertification, and exact supported-runtime post-publish tests.

## Notes

Release code/DAG is implemented and tested, but no live publication was authorized. On 2026-07-10 immutable GitHub releases were disabled and Pages was unconfigured. Enable immutable releases, satisfy ss-0rqn, then publish only frozen manifest-selected bytes and record registry/GitHub provenance plus neutral-directory smoke evidence.
