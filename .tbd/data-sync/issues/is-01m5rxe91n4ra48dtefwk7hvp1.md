---
type: is
id: is-01m5rxe91n4ra48dtefwk7hvp1
title: "PR #59 C4: pin both sides of the entered distinction with vectors; keep contentSchema in _iter_schemas"
kind: bug
status: closed
priority: 3
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rxe40c2nyv4rwytvha8dhy
hold: null
hold_until: null
created_at: 2026-10-25T06:54:47.349Z
updated_at: 2026-10-25T07:16:47.089Z
started_at: 2026-10-25T06:54:53.289Z
closed_at: 2026-10-25T07:16:47.088Z
close_reason: "fixed in e02b064: vectors pin both sides of entered (nested-relative-id-*, embedded-id-resource-internal-reference) and then-with-if stays refused; contentSchema kept in _iter_schemas"
resolution: null
duplicate_of: null
---
Low suggestion. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5641920187. Vectors: lookup target with dir-bearing relative $id; structurally embedded $id with internal ref stays completed; dangling ref under then with if present stays refused.
