---
type: is
id: is-01m5t0dj4xpfdqh0zd0et3d8rv
title: "PR #64 E1: Python compile writer folds a CRLF inside a string value"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0dhtbty9r2zjty30vcjq9
created_at: 2026-10-25T17:06:04.061Z
updated_at: 2026-10-25T17:26:19.938Z
closed_at: 2026-10-25T17:26:19.937Z
close_reason: "Fixed in ad69d3b (PR #64): compile.py forces double-quoted style when the string holds any CR; parity fixture control_text carries a CRLF; both runtimes read back the exact model text; writer->reader sweep Python->TS 0 differences."
resolution: null
duplicate_of: null
---
Medium. compile.py _yaml_dump: force double-quoted style when the string contains \r so \r\n is escaped; parity fixture with a CRLF default.
