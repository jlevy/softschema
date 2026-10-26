---
type: is
id: is-01m5sv1f344pttkfzc12hbzdt9
title: "PR #64 D5: TS preflight error path without array materialization"
kind: chore
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T15:32:04.836Z
updated_at: 2026-10-25T16:25:57.291Z
closed_at: 2026-10-25T16:25:57.291Z
close_reason: "Fixed in 04b6c3e (PR #64): checkPortableText counts line and column with indexOf/charCodeAt loops, no match() array or spread on the error path."
resolution: null
duplicate_of: null
---
Low. portable.ts checkPortableText column count materializes [...before.slice(lineStart)].
