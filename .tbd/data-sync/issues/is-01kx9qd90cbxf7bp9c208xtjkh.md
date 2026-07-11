---
type: is
id: is-01kx9qd90cbxf7bp9c208xtjkh
title: "Step 6: Correct identities, compiler boundaries, and annotations"
kind: task
status: open
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - compiler
  - api
dependencies:
  - type: blocks
    target: is-01kx9qd97f0ekaq63mrc8f9f0z
  - type: blocks
    target: is-01kx9qd9qmjfhmv9egzc34rwtj
parent_id: is-01kx9n8xq83ng2r748pfrtd88e
created_at: 2026-07-11T23:15:12.011Z
updated_at: 2026-07-11T23:15:36.806Z
---
Validate logical contract IDs at every construction, registry, and compiler boundary; separate optional absolute schema IDs from contracts; require contracts for compilation; reserve root x-softschema; validate only retained field annotations; and make drift checks strict-UTF-8, portable, boolean-safe, canonical, and atomic. Acceptance: the paired compiler APIs match the spec, official sidecars have one clean identity model, and shared identity/compiler/annotation vectors pass.
