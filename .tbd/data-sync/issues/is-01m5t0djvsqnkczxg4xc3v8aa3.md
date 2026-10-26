---
type: is
id: is-01m5t0djvsqnkczxg4xc3v8aa3
title: "PR #64 E3: repair escape rule rewrites flow collections, comments, anchors and tags into strings"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0dhtbty9r2zjty30vcjq9
created_at: 2026-10-25T17:06:04.793Z
updated_at: 2026-10-25T17:26:18.723Z
closed_at: 2026-10-25T17:26:18.723Z
close_reason: "Fixed in ad69d3b (PR #64): escape rule and quoting pass rewrite only values that can begin a plain scalar (c-indicator guard, both runtimes); flow collections, comments, anchors, tags stay parse errors; vectors next_line_in_flow_sequence/_mapping/_comment_value/_after_anchor/_after_tag and flow_mapping_beside_a_line_needing_quotes; reviewer's 55-fixture harness: 0 diffs."
resolution: null
duplicate_of: null
---
Medium. repair.py/repair.ts: only genuine plain or quoted scalar values; indicator guard also in the quoting pass; vectors.
