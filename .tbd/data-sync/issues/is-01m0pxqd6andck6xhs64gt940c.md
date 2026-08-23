---
type: is
id: is-01m0pxqd6andck6xhs64gt940c
title: "PR #42 review R4: alternatives nested in a fragment lose all enforcement"
kind: task
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m0pxqbkgrdn1bkyr2d76w67k
created_at: 2026-08-23T09:02:48.522Z
updated_at: 2026-08-23T09:17:55.157Z
closed_at: 2026-08-23T09:17:55.157Z
close_reason: Documented and pinned in 5aa2037 (alternatives_inside_fragment gap vector); code fix folded into ss-p32o, which now covers both directions of the anyOf branch-closure decision.
resolution: null
duplicate_of: null
---
allOf: [{anyOf: [...]}] closes nothing; identical top-level anyOf rejects. Wrapping in allOf is a no-op refactor that silently disables enforcement. Same family as ss-p32o, opposite direction. Document + vector; code fix waits on the ss-p32o branch-closure decision.
