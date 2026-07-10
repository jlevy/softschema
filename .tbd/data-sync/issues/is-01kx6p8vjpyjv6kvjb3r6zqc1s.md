---
type: is
id: is-01kx6p8vjpyjv6kvjb3r6zqc1s
title: Make post-open release byte-limit regression cross-version
kind: bug
status: closed
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - tests
  - release
  - python
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T18:57:35.317Z
updated_at: 2026-07-10T19:01:49.499Z
closed_at: 2026-07-10T19:01:49.498Z
close_reason: Made the post-open byte-limit test mock lstat/fstat consistently across supported Python versions; full suite passes.
---
The post-open JSON byte-limit regression monkeypatched Path.stat, but Path.lstat delegates differently across Python 3.13 and 3.14 after the descriptor-reader refactor. Mock lstat and fstat consistently so the test proves limit+1 enforcement after open on every supported Python version.
