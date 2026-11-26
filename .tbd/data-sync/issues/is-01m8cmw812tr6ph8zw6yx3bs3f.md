---
type: is
id: is-01m8cmw812tr6ph8zw6yx3bs3f
title: "PR #78 C1: Isolate private cache data from public record mutations"
kind: bug
status: closed
priority: 1
version: 3
delegate: codex@spud10.local
labels: []
dependencies: []
parent_id: is-01m8cmv706qkqr4n2mhhnbhw3x
hold: null
hold_until: null
created_at: 2026-11-26T19:21:20.161Z
updated_at: 2026-11-26T19:29:49.013Z
started_at: 2026-11-26T19:21:21.037Z
closed_at: 2026-11-26T19:29:49.013Z
close_reason: "Fixed in SoftSchema PR #78 at e6ee08f. Published disposition lists regression evidence for this finding. All 19 GitHub checks passed."
resolution: null
duplicate_of: null
---
packages/python/src/softschema/collection.py:303 and packages/typescript/src/collection.ts:322.

Review: https://github.com/jlevy/softschema/pull/78#pullrequestreview-6079441463
