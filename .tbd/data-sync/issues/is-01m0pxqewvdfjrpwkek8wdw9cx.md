---
type: is
id: is-01m0pxqewvdfjrpwkek8wdw9cx
title: "PR #42 review R8: multi-key unevaluatedProperties collapse is verified nowhere"
kind: task
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01m0pxqbkgrdn1bkyr2d76w67k
created_at: 2026-08-23T09:02:50.267Z
updated_at: 2026-08-23T09:17:56.417Z
closed_at: 2026-08-23T09:17:56.417Z
close_reason: "Fixed in 5aa2037: two-key collapse case added to both suites."
resolution: null
duplicate_of: null
---
Behavior correct (one record, both engines) but unpinned — e2e tests use one undeclared key, the unit test feeds synthetic additionalProperties records. Add the {first,last,bogus,other} case to both suites.
