---
type: is
id: is-01kx61rer0yvpgpbvp24bjtd26
title: Provision and verify the protected github-release environment
kind: task
status: open
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - live-state
dependencies:
  - type: blocks
    target: is-01kx5fvvr8jfgg5bf70vr9h5kj
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:59:06.367Z
updated_at: 2026-07-10T13:03:32.438Z
---
Before protected-tag execution, create or verify the github-release environment with v* deployment restriction, required reviewer approval, and no admin bypass. Record authenticated API evidence. The current environment inventory contains only pypi and npm, so a workflow reference alone would auto-create an unprotected environment.

## Notes

Read-only GitHub API verification on 2026-07-10 returned exactly the pypi and npm environments; github-release was absent. Immutable releases returned false and Pages returned HTTP 404. Code/docs now classify this as a live prerequisite. A credentialed administrator must provision/re-read the environment before any tag execution; this task intentionally remains open.
