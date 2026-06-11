---
type: is
id: is-01ktsqthfyrkqy7xehrahwdvpd
title: "P4: Test polish (rename coverage.test.ts; capture stdout in in-process test; document corpus update workflow)"
kind: task
status: in_progress
priority: 3
version: 2
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:43:12.126Z
updated_at: 2026-06-11T06:20:34.852Z
---
FILE SCOPE: coverage.test.ts, cli-inprocess.test.ts, tests/golden/README.md.
- Rename coverage.test.ts to reflect its content (it is real unit tests for models/errors/compile/validate, not coverage gaming).
- in-process CLI test: capture stdout to a buffer instead of globally stubbing process.stdout.write.
- Document the golden corpus update workflow (the exact tryscript --update/expand command) in tests/golden/README.md.
Refs review TS 4.4/4.5, parity testing.
