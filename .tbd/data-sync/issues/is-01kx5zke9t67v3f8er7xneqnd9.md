---
type: is
id: is-01kx5zke9t67v3f8er7xneqnd9
title: Bound release manifest subject and aggregate bytes
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - release
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:21:24.921Z
updated_at: 2026-07-10T12:41:13.733Z
closed_at: 2026-07-10T12:39:24.646Z
close_reason: Added 512 MiB per-subject and 1 GiB aggregate manifest limits enforced before reads/downloads, with adversarial tests in the 36-test release-state suite.
---
Release manifest subject sizes are only nonnegative integers, so downstream verification may attempt arbitrarily large or sparse assets. Add kind-aware or conservative per-subject and aggregate byte caps before download/read/hash, enforce them in manifest parsing, and add adversarial tests.
