---
type: is
id: is-01kx9qc63sd4avxxp4h7ekev8q
title: "Step 1: Baseline defects and choose the hard-cut surface"
kind: task
status: open
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - planning
  - api
dependencies:
  - type: blocks
    target: is-01kx9qd83rhjpngwe7qkpdzqff
parent_id: is-01kx9n8xq83ng2r748pfrtd88e
created_at: 2026-07-11T23:14:36.280Z
updated_at: 2026-07-11T23:15:35.042Z
---
Record current main exports, CLI flags, result fields, source/test counts, and validation commands. Attach one minimal failing reproduction and trust-boundary note to every applicable defect row in the spec; confirm every excluded PR #20 category remains excluded. Specify the final paired Python/TypeScript API and CLI surface with no deprecated aliases, compatibility wrappers, or dual result shapes. Acceptance: the spec contains the final surface and each of the 24 applicable rows has a reproducible failing case or is reclassified explicitly.
