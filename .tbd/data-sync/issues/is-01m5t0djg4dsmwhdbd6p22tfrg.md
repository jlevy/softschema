---
type: is
id: is-01m5t0djg4dsmwhdbd6p22tfrg
title: "PR #64 E2: TS compile writer emits a raw tab in a plain scalar and a bare = that ruamel refuses"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0dhtbty9r2zjty30vcjq9
created_at: 2026-10-25T17:06:04.420Z
updated_at: 2026-10-25T17:26:20.240Z
closed_at: 2026-10-25T17:26:20.240Z
close_reason: "Fixed in ad69d3b (PR #64): compile.ts renderYaml forces QUOTE_DOUBLE for strings holding a tab or equal to '='; parity fixture control_text; sweep TS->Python 4,686 cases, 0 unreadable, 0 drift."
resolution: null
duplicate_of: null
---
Medium. compile.ts renderYaml: QUOTE_DOUBLE for strings with a tab or exactly =; conformance sweep.
