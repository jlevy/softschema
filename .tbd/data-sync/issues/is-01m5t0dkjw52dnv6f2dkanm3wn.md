---
type: is
id: is-01m5t0dkjw52dnv6f2dkanm3wn
title: "PR #64 E5: escaping a lone CR turns a CR-delimited file into one string"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0dhtbty9r2zjty30vcjq9
created_at: 2026-10-25T17:06:05.532Z
updated_at: 2026-10-25T17:26:19.351Z
closed_at: 2026-10-25T17:26:19.351Z
close_reason: "Fixed in ad69d3b (PR #64): a value holding a lone CR is never escaped (returns None/null) in both runtimes; vectors lone_cr_in_value_is_not_repaired, cr_only_file_is_not_repaired; control_characters_in_plain_value vector no longer carries CR; spec sentence."
resolution: null
duplicate_of: null
---
Medium. Leave a lone CR out of the escape rule; CR-only file vector; spec sentence.
