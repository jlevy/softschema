---
type: is
id: is-01m5rztbvqna37z0m4kyjx5ex4
title: "PR #59 D2: walk follows contains/unevaluated* subschemas Ajv skips at compile time"
kind: bug
status: closed
priority: 3
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rztad5krc4zxt6mw8qwhw7
hold: null
hold_until: null
created_at: 2026-10-25T07:36:20.598Z
updated_at: 2026-10-25T07:46:07.212Z
started_at: 2026-10-25T07:36:25.710Z
closed_at: 2026-10-25T07:46:07.212Z
close_reason: "fixed in 7aded61: walk skips inert/impossible contains, unevaluatedProperties beside additionalProperties, unevaluatedItems beside items or compiled contains (read from Ajv sources); unreached vectors ordinary; reached shapes and allOf tracking pinned as engine_deviations"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5642075680 (= E1 for contains). Fix: match Ajv skip conditions in the walk; vectors; pin where exact matching impossible.
