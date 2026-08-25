---
type: is
id: is-01m0vcqpwktrpf5f5fq85dj2nx
title: Specify optional native semantic validator extensions
kind: feature
status: open
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m0tenataem0p1w6xmrynypvt
created_at: 2026-08-25T02:42:04.818Z
updated_at: 2026-08-25T02:50:54.363Z
---
Specify language-native Pydantic/Zod validation as an explicit additive semantic layer over the portable structural contract, not an implicit fallback. Define required-versus-absent semantics, behavior when a required native validator is unavailable, raw-value and transformation rules, contract/version identity beyond schema_sha256, trusted host-side resolution, error portability, and paired-conformance expectations when both runtimes implement the extension.
