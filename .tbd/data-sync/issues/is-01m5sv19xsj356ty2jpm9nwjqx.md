---
type: is
id: is-01m5sv19xsj356ty2jpm9nwjqx
title: "PR #64 B1: compile writers emit raw U+0085/U+2028/U+2029 that the preflight rejects"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T15:31:59.545Z
updated_at: 2026-10-25T16:25:54.071Z
closed_at: 2026-10-25T16:25:54.071Z
close_reason: "Fixed in 8762c2b (PR #64): both compile writers force strings with rejected characters into double-quoted style and emit \\N/\\L/\\P/\\xHH; compile runs the preflight on its own output; compile --check reports an unreadable committed sidecar as drift; schema_invalid names the schema path; parity fixture carries U+0085/U+2028/U+2029 in description/default/enum with identical schema_sha256 6db7ff23...; spec covers schema files."
resolution: null
duplicate_of: null
---
High. compile.py:166-178, compile.ts:96, _portable.py:145, validate.py:137. Escape in both writers, run preflight on compile output, shared vector, name schema path in schema_invalid.
