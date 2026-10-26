---
type: is
id: is-01m5sv1cb1devxrn44sk1pey1e
title: "PR #64 B8: preflight message: file-relative line numbers, lone CR counted, name the escape"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T15:32:02.016Z
updated_at: 2026-10-25T16:25:55.712Z
closed_at: 2026-10-25T16:25:55.712Z
close_reason: "Fixed in 04b6c3e (PR #64): frontmatter-md diagnostics shift every 'line N, column M' (and ruamel's '(line: N)') by the fence so they count from the top of the file, for the preflight and engine messages; the preflight message names the escape to write; a lone CR is itself rejected (C1) so the CR line-count gap is moot. Goldens and unit tests updated in both runtimes."
resolution: null
duplicate_of: null
---
Low. _portable.py:119-140, portable.ts:95-109.
