---
type: is
id: is-01m0pxqe36we0930d6d87gczv7
title: "PR #42 review R6: properties under \\`not\\` count as declarations and close the schema to nothing"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m0pxqbkgrdn1bkyr2d76w67k
created_at: 2026-08-23T09:02:49.445Z
updated_at: 2026-08-23T09:17:55.787Z
closed_at: 2026-08-23T09:17:55.787Z
close_reason: "Fixed in 5aa2037: not excluded from the declares-scan in both engines."
resolution: null
duplicate_of: null
---
not is a prohibition, not a declaration, and contributes no annotations, so the admissible set becomes empty. Verified {a:1} valid under soft, invalid under enforced, both engines. Skip not in the declares-scan; keep it in _FRAGMENT_APPLICATORS.
