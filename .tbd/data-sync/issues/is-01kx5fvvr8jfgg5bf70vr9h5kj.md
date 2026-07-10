---
type: is
id: is-01kx5fvvr8jfgg5bf70vr9h5kj
title: Verify live publisher authorization and release preflight
kind: task
status: open
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - security
  - operations
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T07:46:23.623Z
updated_at: 2026-07-10T13:03:49.097Z
---
Complete the live release-operations gates that cannot be proven from source alone: merge the release candidate through a real protected PR with every required context, run and verify the manual preflight workflow, authenticate to PyPI and npm to configure/re-certify the exact trusted publishers and protected environments, verify repository/environment/ruleset state through APIs, and record durable evidence before ss-trn7 may publish. This bead intentionally separates external account and GitHub state from ss-o21w's code-side artifact-boundary implementation so conformance work is not blocked by credentials.

## Notes

Read-only API audit on 2026-07-10 confirmed protected main/v* rulesets, SHA-pinned Actions policy, and pypi/npm reviewer-gated environments. It also confirmed github-release is absent, immutable releases are disabled, Pages is absent, and registry-side trusted-publisher authorization/manual protected preflight were not executed. Source tests cannot substitute for those credentialed live checks; ss-8dt9 tracks the missing GitHub release environment.
