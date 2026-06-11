---
type: is
id: is-01kttqmh530v0v9451n5tn1xh1
title: "[deferred] Single-read CLI plumbing for validate (efficiency polish)"
kind: task
status: open
priority: 4
version: 1
labels: []
dependencies: []
created_at: 2026-06-11T06:59:09.602Z
updated_at: 2026-06-11T06:59:09.602Z
---
From Phase 3 binding inference (ss-z3gy): the CLI still reads/parses the document twice (binding inference, then validate_artifact). Spec-conformance half landed; eliminating the double read is an efficiency refactor in both CLIs.
