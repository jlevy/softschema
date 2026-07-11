---
type: is
id: is-01kx9qd8j23ketnj5n06a91vfd
title: "Step 4: Close JSON Schema validation semantics"
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - validation
  - parity
dependencies:
  - type: blocks
    target: is-01kx9qd9qmjfhmv9egzc34rwtj
parent_id: is-01kx9n8xq83ng2r748pfrtd88e
created_at: 2026-07-11T23:15:11.553Z
updated_at: 2026-07-11T23:45:03.074Z
closed_at: 2026-07-11T23:45:03.073Z
close_reason: Validation now uses closed in-memory resource registries, rejects duplicate identities and unavailable refs, normalizes schema failures, treats formats as annotations, and checks a bounded portable pattern subset.
---
Make schema validation offline, resolve only root/embedded/explicitly loaded local resources, reject identity collisions and unavailable references, and normalize all readable invalid schemas into stable schema_invalid reasons. Align format as annotation-only and enforce a small common native-regex syntax without a custom regex engine. Acceptance: shared reference, local-resource, schema-failure, format, and pattern vectors pass in both runtimes and no retrieval path exists.
