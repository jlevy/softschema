---
type: is
id: is-01m8cmw12z0xfvg194ej6w680m
title: "PR #78 B1: Preserve structural execution in collection records"
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
created_at: 2026-11-26T19:21:13.051Z
updated_at: 2026-11-26T19:29:48.932Z
started_at: 2026-11-26T19:21:13.749Z
closed_at: 2026-11-26T19:29:48.931Z
close_reason: "Fixed in SoftSchema PR #78 at e6ee08f. Published disposition lists regression evidence for this finding. All 19 GitHub checks passed."
resolution: null
duplicate_of: null
---
packages/python/src/softschema/collection.py:335 and packages/typescript/src/collection.ts:355.

Review: https://github.com/jlevy/softschema/pull/78#pullrequestreview-6079441293
