---
type: is
id: is-01m8cmwb6grqpvrfg4yamz8yea
title: "PR #78 C4: Document and enforce runtime-local collection snapshots"
kind: bug
status: closed
priority: 2
version: 3
delegate: codex@spud10.local
labels: []
dependencies: []
parent_id: is-01m8cmv706qkqr4n2mhhnbhw3x
hold: null
hold_until: null
created_at: 2026-11-26T19:21:23.401Z
updated_at: 2026-11-26T19:29:49.046Z
started_at: 2026-11-26T19:21:24.072Z
closed_at: 2026-11-26T19:29:49.046Z
close_reason: "Fixed in SoftSchema PR #78 at e6ee08f. Published disposition lists regression evidence for this finding. All 19 GitHub checks passed."
resolution: null
duplicate_of: null
---
packages/python/src/softschema/collection.py:86 and packages/typescript/src/collection.ts:88.

Review: https://github.com/jlevy/softschema/pull/78#pullrequestreview-6079441463
