---
type: is
id: is-01kx9qdakxzyp25ef7kyyd0xnr
title: "Step 13: Run the full matrix and perform the deletion pass"
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - validation
  - cleanup
dependencies:
  - type: blocks
    target: is-01kx9qdatz2pmwz6r61kw4czdp
parent_id: is-01kx9n8xq83ng2r748pfrtd88e
created_at: 2026-07-11T23:15:13.659Z
updated_at: 2026-07-12T03:11:57.102Z
closed_at: 2026-07-12T03:11:57.101Z
close_reason: Full Python, TypeScript, golden, parity, package, and isolated-install matrix passed; deleted seven unreferenced fixtures and confirmed every retained fixture has a consumer.
---
Run Python lint/types/tests, TypeScript lint/typecheck/tests/coverage, shared vectors, Python/Node CLI goldens, Bun-only source cases, canonical digest parity, wheel/npm builds, publint, isolated package smokes, and nonpublishing release dry run. Compare source/test/fixture/workflow growth to baseline, remove helpers and tests without unique responsibility, and enforce the 3000-line review target and 5000-line failure gate. Acceptance: all gates pass and the working tree contains no prohibited subsystem or redundant compatibility code.
