---
type: is
id: is-01kx9qd83rhjpngwe7qkpdzqff
title: "Step 2: Establish shared vectors and test ownership"
kind: task
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - testing
  - parity
dependencies:
  - type: blocks
    target: is-01kx9qd8axb257dq5xv38m5jt2
  - type: blocks
    target: is-01kx9qd9ghwrm3avgkg2vdf0fj
parent_id: is-01kx9n8xq83ng2r748pfrtd88e
created_at: 2026-07-11T23:15:11.096Z
updated_at: 2026-07-11T23:29:59.389Z
closed_at: 2026-07-11T23:29:59.388Z
close_reason: Added one readable shared YAML corpus, loaders in both runtimes, and an explicit primary-owner map without a conformance platform.
---
Create the minimal shared YAML vector organization and behavior-to-primary-owner map before runtime changes. Cover artifact input, portable values, local references, malformed schemas, format, patterns, canonicalization, enforcement, identity, compiler annotations, SchemaView, and digests. Keep the existing tryscript runner only for a few end-to-end CLI journeys. Acceptance: both runtimes can consume the same YAML vectors, every behavior has one primary owner, and no separate conformance platform or generated JSON corpus exists.
