---
type: is
id: is-01kz5wznv3kxjxvfvz598hs4q9
title: TypeScript validateStructural recompiles Ajv on every call
kind: feature
status: closed
priority: 2
version: 2
labels: []
dependencies: []
created_at: 2026-08-04T08:07:03.778Z
updated_at: 2026-08-22T23:15:14.993Z
closed_at: 2026-08-22T23:15:14.992Z
close_reason: "Fixed in v0.6.2 (PR #39, commit d209338). validateStructural now memoizes the compiled validator, mirroring the Python _cached_validator shipped in v0.5.0. As the bead suggested, the key is the schema content (JSON-serialized, since TS receives a parsed object rather than a path) plus the strictExtras overlay flag; validation with resources supplied builds fresh in both runtimes rather than risk a wrong key, and only a schema that compiles is cached. The schema-identity and pattern checks moved inside the cached build, since they are pure functions of the same inputs. Measured on a repeated validation of the movie example: ~17ms to ~0.03ms per call. Also exports clearValidatorCache, closing the parity gap with clear_validator_cache."
---
packages/typescript/src/validate.ts:151-160 constructs a fresh Ajv2020 and compiles per call, the same cost PR #26 fixed in Python. Takes a parsed schemaObject not a path, so a content hash is the key both runtimes can share. Follow-up to PR #26.
