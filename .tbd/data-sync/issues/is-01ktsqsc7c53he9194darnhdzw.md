---
type: is
id: is-01ktsqsc7c53he9194darnhdzw
title: "P2: CI cross-implementation diff job (run both CLIs on same inputs, byte-compare)"
kind: task
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:33.963Z
updated_at: 2026-06-10T22:27:25.437Z
closed_at: 2026-06-10T22:27:25.436Z
close_reason: null
---
FILE SCOPE: .github/workflows/ci.yml (+ small script under tests/golden/).
- New step/job: run softschema-py and node dist/cli.js on the same input set, byte-compare outputs, fail on any difference. Reports parity failures AS parity failures rather than as one side drifting from committed golden files. Blocked by P2 harness bead.
