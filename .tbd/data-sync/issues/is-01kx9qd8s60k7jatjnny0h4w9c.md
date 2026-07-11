---
type: is
id: is-01kx9qd8s60k7jatjnny0h4w9c
title: "Step 5: Make canonicalization, digests, and enforcement semantic"
kind: task
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - compiler
  - parity
dependencies:
  - type: blocks
    target: is-01kx9qd90cbxf7bp9c208xtjkh
  - type: blocks
    target: is-01kx9qd9qmjfhmv9egzc34rwtj
parent_id: is-01kx9n8xq83ng2r748pfrtd88e
created_at: 2026-07-11T23:15:11.781Z
updated_at: 2026-07-11T23:53:55.379Z
closed_at: 2026-07-11T23:53:55.378Z
close_reason: Canonicalization now preserves annotations and traverses all recognized subschema positions; digest encoding sorts bytes directly; unsafe composed closure returns enforcement_unsupported; paired compiler output remains identical.
---
Restrict canonicalization to recognized subschema positions, preserve annotation and unknown data, normalize only documented semantic no-ops, and specify set-like ordering. Compare CLI JSON structurally and use an RFC 8785-compatible representation only for compiled-schema digests. Apply enforced closure only when safe and return enforcement_unsupported otherwise. Acceptance: before/after validation invariants and shared canonicalization, digest, and enforcement vectors pass without a general CLI JSON serializer.
