---
type: is
id: is-01kx5fvvr8jfgg5bf70vr9h5kj
title: Verify live publisher authorization and release preflight
kind: task
status: open
priority: 1
version: 3
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
updated_at: 2026-07-10T11:52:50.743Z
---
Complete the live release-operations gates that cannot be proven from source alone: merge the release candidate through a real protected PR with every required context, run and verify the manual preflight workflow, authenticate to PyPI and npm to configure/re-certify the exact trusted publishers and protected environments, verify repository/environment/ruleset state through APIs, and record durable evidence before ss-trn7 may publish. This bead intentionally separates external account and GitHub state from ss-o21w's code-side artifact-boundary implementation so conformance work is not blocked by credentials.

## Notes

Read-only audit on 2026-07-10 observed active main/v* rulesets, required CI contexts, full-SHA Actions pinning, and pypi/npm environments restricted to v* tags with reviewer gates. GitHub immutable releases were disabled. Still required: enable/re-read immutable releases, merge through a protected PR, run manual preflight, and authenticate to verify both registry trusted-publisher claims.
