---
type: is
id: is-01kx5yxj8s3x7g93tqxcmks7hr
title: Gate the PyPI README bootstrap pin from release metadata
kind: bug
status: open
priority: 2
version: 1
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - release
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:09:28.088Z
updated_at: 2026-07-10T12:09:28.088Z
---
The PyPI-facing packages/python/README.md hard-codes the Python bootstrap pin but bootstrap/release-pin tests do not include it. Add it to the public executable surfaces and assert the exact release-metadata Python pin so version bumps cannot leave stale registry instructions.
