---
type: is
id: is-01m0pxqcd1gvt1kzz5f3tbtyvw
title: 'PR #42 review R2: CHANGELOG claim \"no document silently becomes valid\" is false'
kind: bug
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01m0pxqbkgrdn1bkyr2d76w67k
created_at: 2026-08-23T09:02:47.712Z
updated_at: 2026-08-23T09:17:54.512Z
closed_at: 2026-08-23T09:17:54.512Z
close_reason: "Fixed in 5aa2037: claim scoped to composition roots in CHANGELOG and plan; What enforced does not close added to the spec; both shapes pinned as enforcement_gaps vectors."
resolution: null
duplicate_of: null
---
CHANGELOG.md and plan Compatibility. R3 and R4 shapes were refused on main and are silently valid now. Verified both against main. Scope the claim to composition roots and add a what-enforced-does-not-close list.
