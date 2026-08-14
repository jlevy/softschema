---
type: is
id: is-01kz5wznv3kxjxvfvz598hs4q9
title: TypeScript validateStructural recompiles Ajv on every call
kind: feature
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-08-04T08:07:03.778Z
updated_at: 2026-08-04T08:07:03.778Z
---
packages/typescript/src/validate.ts:151-160 constructs a fresh Ajv2020 and compiles per call, the same cost PR #26 fixed in Python. Takes a parsed schemaObject not a path, so a content hash is the key both runtimes can share. Follow-up to PR #26.
