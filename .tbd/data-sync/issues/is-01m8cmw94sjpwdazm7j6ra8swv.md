---
type: is
id: is-01m8cmw94sjpwdazm7j6ra8swv
title: "PR #78 C2: Preserve input membership across successive partial walks"
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
created_at: 2026-11-26T19:21:21.304Z
updated_at: 2026-11-26T19:29:49.022Z
started_at: 2026-11-26T19:21:22.333Z
closed_at: 2026-11-26T19:29:49.022Z
close_reason: "Fixed in SoftSchema PR #78 at e6ee08f. Published disposition lists regression evidence for this finding. All 19 GitHub checks passed."
resolution: null
duplicate_of: null
---
packages/python/src/softschema/collection.py:472 and packages/typescript/src/collection.ts:461.

Review: https://github.com/jlevy/softschema/pull/78#pullrequestreview-6079441463
