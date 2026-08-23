---
type: is
id: is-01m0pxqdnb9qwtfj3h7qg5mdj4
title: "PR #42 review R5: guide cross-field example makes a false additionalProperties claim"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m0pxqbkgrdn1bkyr2d76w67k
created_at: 2026-08-23T09:02:49.003Z
updated_at: 2026-08-23T09:17:55.477Z
closed_at: 2026-08-23T09:17:55.476Z
close_reason: "Fixed in 5aa2037: guide bullet rewritten — budget_spent is declared in the root's own properties, so additionalProperties would admit it."
resolution: null
duplicate_of: null
---
docs/softschema-guide.md. budget_spent is declared in the root properties, so root additionalProperties:false sees it. Verified: with explicit additionalProperties:false the example validates and the conditional still fires. Rewrite the bullet.
