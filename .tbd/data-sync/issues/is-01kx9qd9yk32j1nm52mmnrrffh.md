---
type: is
id: is-01kx9qd9yk32j1nm52mmnrrffh
title: "Step 10: Consolidate unit tests and CLI goldens"
kind: task
status: open
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - testing
  - cleanup
dependencies:
  - type: blocks
    target: is-01kx9qdakxzyp25ef7kyyd0xnr
parent_id: is-01kx9n8xq83ng2r748pfrtd88e
created_at: 2026-07-11T23:15:12.978Z
updated_at: 2026-07-11T23:15:38.049Z
---
Delete redundant or implementation-detail tests after the final integration. Keep shared YAML vectors as the primary portable contract, runtime units only for adapters, and a few full-state tryscript CLI journeys. Preserve meaningful coverage floors while reporting behavior coverage, suite runtime, and test/fixture lines. Acceptance: no behavior is repeated across layers without a documented distinct failure mode and the full suite remains readable and fast.
