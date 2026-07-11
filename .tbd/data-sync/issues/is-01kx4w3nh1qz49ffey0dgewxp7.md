---
type: is
id: is-01kx4w3nh1qz49ffey0dgewxp7
title: Make dual-registry releases idempotent and verify published artifacts
kind: task
status: closed
priority: 1
version: 11
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
updated_at: 2026-07-11T23:13:49.574Z
closed_at: 2026-07-11T23:13:49.574Z
close_reason: "Superseded by the clean main-based minimal hardening plan; PR #20 will not be merged and its remaining conformance/recovery/live-release work is intentionally excluded."
---
Freeze the full 0.3 release candidate, then publish external-manifest-verified bytes through a draft-assets/attestation → PyPI+npm → final-release DAG. Implement ecosystem version/pin/prerelease mapping, registry-specific state/recovery, SPDX SBOM and current GitHub attestation verification, npm trusted-publisher recertification, and exact supported-runtime post-publish tests.

## Notes

All source-side orchestration and final security closures are implemented and tested: exact registry/GitHub classifiers, exact npm URI SAN, 90-day initial transfer plus exact-commit-attested durable recovery, authenticated closed checksum inventory, pre-write extraction budgets, manifest bounds, latest/prerelease postconditions, immediate immutable-policy recheck, and post-publish provenance hooks. No registry bytes, tag, or release were published. Completion requires protected github-release environment ss-8dt9, ss-0rqn authorization, immutable releases enabled, and an authorized real protected-tag dual-registry run.
