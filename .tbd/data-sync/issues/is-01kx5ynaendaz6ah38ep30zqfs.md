---
type: is
id: is-01kx5ynaendaz6ah38ep30zqfs
title: Correct golden-corpus coverage and exit-code documentation
kind: bug
status: open
priority: 2
version: 1
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - testing
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:04:57.940Z
updated_at: 2026-07-10T12:04:57.940Z
---
tests/golden/README.md attributes unsupported batch coverage to batch-diagnostics.md and documents exit 2 for whitespace-only and unterminated frontmatter even though the executable goldens assert exit 1. Align the README with the actual scenario and unit-test ownership.
