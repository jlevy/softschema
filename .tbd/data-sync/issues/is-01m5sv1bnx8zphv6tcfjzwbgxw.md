---
type: is
id: is-01m5sv1bnx8zphv6tcfjzwbgxw
title: "PR #64 B6: repair rewrites a raw rejected character in a single-line value as a double-quoted escape"
kind: feature
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T15:32:01.341Z
updated_at: 2026-10-25T16:25:55.157Z
closed_at: 2026-10-25T16:25:55.157Z
close_reason: "Fixed in b36cf2e (PR #64): repair rewrites a rejected raw character inside a single-line plain/single-quoted/double-quoted value as a double-quoted escape, one yaml_escaped_character record per value; keys, comments, block scalars stay errors; nothing guessed. Nine yaml_repair vectors, unit tests, golden journey, spec/skill/guide updated. Also fixed TS MAPPING_LINE '.' divergence and TS round-trip dump re-escaping."
resolution: null
duplicate_of: null
---
Medium. repair.py:170-216, repair.ts. Narrow deterministic rule: \\N/\\L/\\P/\\xHH, one record per value under a new code; comments/keys/block scalars stay errors; never guess.
