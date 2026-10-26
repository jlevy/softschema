---
type: is
id: is-01m5t0dmmnn2ha64ce7aya3xyz
title: "PR #64 E8: tab inside a plain scalar and plain = split the readers"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0dhtbty9r2zjty30vcjq9
created_at: 2026-10-25T17:06:06.613Z
updated_at: 2026-10-25T17:26:20.555Z
closed_at: 2026-10-25T17:26:20.555Z
close_reason: "Fixed in ad69d3b (PR #64): TS rejects a raw tab in a plain scalar or as block-context spacing via a yaml CST walk after the engine parse (yaml_parse_error); Python constructs plain '=' as the string '='. Eleven portable_values vectors; spec; CHANGELOG Compatibility."
resolution: null
duplicate_of: null
---
Medium. Make the readers agree: Python constructs plain = as the string; TS rejects a raw tab in a plain scalar as yaml_parse_error like ruamel.
