---
type: is
id: is-01ktsqsbrrhh45t4tk5gb98jza
title: "P2: CI runs golden under Node+Bun (TS) and across the Python matrix"
kind: task
status: in_progress
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:33.496Z
updated_at: 2026-06-10T22:07:28.006Z
---
FILE SCOPE: .github/workflows/ci.yml.
- typescript job: run tests/golden/run.sh with SOFTSCHEMA_IMPL=ts (Node, via setup-node pin) AND ts-bun (Bun).
- golden job: run the Python corpus across the supported Python matrix, not only 3.13.
Blocked by P2 harness bead.
