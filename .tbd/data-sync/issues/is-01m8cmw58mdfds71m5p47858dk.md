---
type: is
id: is-01m8cmw58mdfds71m5p47858dk
title: "PR #78 B5: Report an unreadable root as a CLI usage failure"
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
created_at: 2026-11-26T19:21:17.330Z
updated_at: 2026-11-26T19:29:48.976Z
started_at: 2026-11-26T19:21:17.938Z
closed_at: 2026-11-26T19:29:48.976Z
close_reason: "Fixed in SoftSchema PR #78 at e6ee08f. Published disposition lists regression evidence for this finding. All 19 GitHub checks passed."
resolution: null
duplicate_of: null
---
packages/python/src/softschema/collection.py:182 and packages/typescript/src/collection.ts:171.

Review: https://github.com/jlevy/softschema/pull/78#pullrequestreview-6079441293
