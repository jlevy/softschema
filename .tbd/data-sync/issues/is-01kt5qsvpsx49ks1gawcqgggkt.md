---
type: is
id: is-01kt5qsvpsx49ks1gawcqgggkt
title: Make TS skill --install writes atomic (parity with schema/generate writes)
kind: task
status: closed
priority: 3
version: 5
spec_path: docs/project/specs/done/plan-2026-06-01-softschema-typescript-zod-parity.md
labels:
  - typescript
dependencies: []
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-03T03:18:01.175Z
updated_at: 2026-07-10T03:49:13.331Z
closed_at: 2026-06-11T05:18:54.217Z
close_reason: null
---
Senior review suggestion (PR #3). skill --install mutates checked-in agent mirrors (.agents/.claude). Less critical than schema/generate writes (which already use atomically), but it is a CLI write path; use the atomic write helper for consistency on the TypeScript side.
