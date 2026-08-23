---
type: is
id: is-01m0pxqct8kbzc5tvgfepj80r1
title: "PR #42 review R3: objects declared inline inside fragments are never closed"
kind: task
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m0pxqbkgrdn1bkyr2d76w67k
created_at: 2026-08-23T09:02:48.135Z
updated_at: 2026-08-23T09:17:54.836Z
closed_at: 2026-08-23T09:17:54.836Z
close_reason: "Documented in 5aa2037: spec What enforced does not close, with the $defs+$ref workaround; pinned as the nested_object_inside_fragment gap vector. Behavior unchanged by design."
resolution: null
duplicate_of: null
---
Sound conservative choice (closing them lexically reintroduces sibling blindness) but an invisible strictness cliff. Document in spec closure section with the \$defs+\$ref workaround; pin with a vector.
