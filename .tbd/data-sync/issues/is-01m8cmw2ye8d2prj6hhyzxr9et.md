---
type: is
id: is-01m8cmw2ye8d2prj6hhyzxr9et
title: "PR #78 B3: Report entry and total byte limits in scan results"
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
created_at: 2026-11-26T19:21:14.957Z
updated_at: 2026-11-26T19:29:48.959Z
started_at: 2026-11-26T19:21:15.684Z
closed_at: 2026-11-26T19:29:48.959Z
close_reason: "Fixed in SoftSchema PR #78 at e6ee08f. Published disposition lists regression evidence for this finding. All 19 GitHub checks passed."
resolution: null
duplicate_of: null
---
packages/python/src/softschema/collection.py:163 and packages/typescript/src/collection.ts:165.

Review: https://github.com/jlevy/softschema/pull/78#pullrequestreview-6079441293
