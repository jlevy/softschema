---
type: is
id: is-01m5t0dkxgsgd2hy3d80qhs0j4
title: "PR #64 E6: quoting pass trims with the host default whitespace set"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0dhtbty9r2zjty30vcjq9
created_at: 2026-10-25T17:06:05.871Z
updated_at: 2026-10-25T17:26:19.663Z
closed_at: 2026-10-25T17:26:19.663Z
close_reason: "Fixed in ad69d3b (PR #64): _value_needs_quoting/_quote_value and TS twins trim only space/tab and open a comment only on [ \\t]+#[ \\t]; vectors next_line_in_comment_of_line_needing_quotes (stays error in both) and bom_before_hash_in_line_needing_quotes (quoted identically in both)."
resolution: null
duplicate_of: null
---
Medium. strip(" \t") and [ \t] comment detection in both quoting passes; vector with U+0085 in the comment of a line needing quoting.
