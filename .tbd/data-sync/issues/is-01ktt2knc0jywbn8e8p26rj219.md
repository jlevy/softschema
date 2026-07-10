---
type: is
id: is-01ktt2knc0jywbn8e8p26rj219
title: "standalone.test.ts: build in beforeAll hits default hook timeout on cold runs"
kind: bug
status: closed
priority: 3
version: 4
spec_path: docs/project/specs/done/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies: []
parent_id: is-01ktt2km937gwscjjj37h82nbr
created_at: 2026-06-11T00:51:41.056Z
updated_at: 2026-07-10T03:49:19.668Z
closed_at: 2026-06-11T00:55:47.763Z
close_reason: null
---
packages/typescript/test/standalone.test.ts:33-35: 'bun run build' runs inside beforeAll with Bun's default hook timeout (~5s); cold/loaded runs get SIGTERM (PR #9 finding 2, P3). Give the hook an explicit generous timeout.
