---
type: is
id: is-01kx9qd8axb257dq5xv38m5jt2
title: "Step 3: Enforce portable artifact input and bounded YAML"
kind: task
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - validation
  - security
dependencies:
  - type: blocks
    target: is-01kx9qd8j23ketnj5n06a91vfd
  - type: blocks
    target: is-01kx9qd8s60k7jatjnny0h4w9c
parent_id: is-01kx9n8xq83ng2r748pfrtd88e
created_at: 2026-07-11T23:15:11.324Z
updated_at: 2026-07-11T23:40:50.173Z
closed_at: 2026-07-11T23:40:50.172Z
close_reason: Added strict bounded UTF-8 reads and portable YAML representation/value checks in two small private helpers; shared artifact, value, and limit vectors pass in both runtimes.
---
Implement stable access versus parse failure reasons, strict UTF-8, the JSON-compatible YAML value domain, and modest byte/depth/node/scalar limits using existing parser representation or event APIs. Reject duplicate/non-string keys, aliases, merge keys, timestamps, tags, unsafe or nonfinite numbers, negative zero, and lone surrogates. Acceptance: shared artifact-input and portable-value vectors pass in Python and TypeScript with no custom YAML parser or incremental construction framework.
