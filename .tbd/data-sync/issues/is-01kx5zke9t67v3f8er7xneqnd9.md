---
type: is
id: is-01kx5zke9t67v3f8er7xneqnd9
title: Bound release manifest subject and aggregate bytes
kind: bug
status: in_progress
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - release
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:21:24.921Z
updated_at: 2026-07-10T12:26:24.068Z
---
Release manifest subject sizes are only nonnegative integers, so downstream verification may attempt arbitrarily large or sparse assets. Add kind-aware or conservative per-subject and aggregate byte caps before download/read/hash, enforce them in manifest parsing, and add adversarial tests.
