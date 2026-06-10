---
type: is
id: is-01kt5qsvpsx49ks1gawcqgggkt
title: Make TS skill --install writes atomic (parity with schema/generate writes)
kind: task
status: open
priority: 3
version: 1
spec_path: docs/project/specs/active/plan-2026-06-01-softschema-typescript-zod-parity.md
labels:
  - typescript
dependencies: []
created_at: 2026-06-03T03:18:01.175Z
updated_at: 2026-06-03T03:18:01.175Z
---
Senior review suggestion (PR #3). skill --install mutates checked-in agent mirrors (.agents/.claude). Less critical than schema/generate writes (which already use atomically), but it is a CLI write path; use the atomic write helper for consistency on the TypeScript side.
