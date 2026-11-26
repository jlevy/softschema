---
type: is
id: is-01m8cmw6vbzbjz240z6zk057gh
title: "PR #78 B7: Reject noninteger and unsafe collection scan bounds"
kind: bug
status: closed
priority: 3
version: 3
delegate: codex@spud10.local
labels: []
dependencies: []
parent_id: is-01m8cmv706qkqr4n2mhhnbhw3x
hold: null
hold_until: null
created_at: 2026-11-26T19:21:18.949Z
updated_at: 2026-11-26T19:29:48.999Z
started_at: 2026-11-26T19:21:19.826Z
closed_at: 2026-11-26T19:29:48.999Z
close_reason: "Fixed in SoftSchema PR #78 at e6ee08f. Published disposition lists regression evidence for this finding. All 19 GitHub checks passed."
resolution: null
duplicate_of: null
---
packages/python/src/softschema/collection.py:381.

Review: https://github.com/jlevy/softschema/pull/78#pullrequestreview-6079441293
