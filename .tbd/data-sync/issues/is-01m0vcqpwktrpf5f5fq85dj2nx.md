---
type: is
id: is-01m0vcqpwktrpf5f5fq85dj2nx
title: Specify optional native semantic validator extensions
kind: feature
status: open
priority: 3
version: 4
labels: []
dependencies: []
parent_id: null
created_at: 2026-08-25T02:42:04.818Z
updated_at: 2026-10-26T03:33:12.330Z
---
Specify language-native Pydantic/Zod validation as an explicit additive semantic layer over the portable structural contract, not an implicit fallback. Define required-versus-absent semantics, behavior when a required native validator is unavailable, raw-value and transformation rules, contract/version identity beyond schema_sha256, trusted host-side resolution, error portability, and paired-conformance expectations when both runtimes implement the extension.

## Notes

Origin: follow-up feature from the PR #44 checked-enforcement review (epic ss-6xya, closed 2026-10-26); detached from it. Partly informed by v0.9.0 (#59): per-layer ValidationExecution (not_run/completed/errored) and the opt-in require= / validate --require semantic now let a host demand that a native validator actually ran, so 'behavior when a required native validator is unavailable' has a host-side answer (check_not_completed). Still open: raw-value and transformation rules, contract/version identity beyond schema_sha256 (the spec says native rules are not covered by it), trusted host-side resolution, error portability, and paired-conformance expectations. Design/spec work; no code started.
