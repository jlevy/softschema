---
type: is
id: is-01kx9qd97f0ekaq63mrc8f9f0z
title: "Step 7: Fix SchemaView, schema paths, and TypeScript model loading"
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - api
  - filesystem
dependencies:
  - type: blocks
    target: is-01kx9qd9qmjfhmv9egzc34rwtj
parent_id: is-01kx9n8xq83ng2r748pfrtd88e
created_at: 2026-07-11T23:15:12.238Z
updated_at: 2026-07-12T00:10:45.625Z
closed_at: 2026-07-12T00:10:45.624Z
close_reason: Implemented snapshot SchemaView parity, identity separation, exact nullable handling, realpath containment, and URL-safe model loading with focused tests.
---
Make SchemaView snapshot inputs, preserve allowed ref-sibling annotations, distinguish exact nullable single values from genuine unions, and expose contract and schema identities separately. Realpath document-controlled schemas before containment checks. Convert trusted TypeScript model paths with pathToFileURL and report clear Node versus Bun extension errors. Acceptance: focused shared SchemaView vectors and runtime-specific filesystem/model-loader tests cover each defect without descriptor race machinery.
