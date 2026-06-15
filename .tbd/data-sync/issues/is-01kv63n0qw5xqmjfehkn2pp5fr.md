---
type: is
id: is-01kv63n0qw5xqmjfehkn2pp5fr
title: "TS: 4 near-duplicate isObject/isMapping guards (canonicalize/compile/schemaView/validate); consider one internal util"
kind: task
status: closed
priority: 3
version: 2
labels: []
dependencies: []
created_at: 2026-06-15T17:00:47.228Z
updated_at: 2026-06-15T17:46:10.001Z
closed_at: 2026-06-15T17:46:10.000Z
close_reason: Consolidated the 4 identical object guards into src/guards.ts isMapping (SchemaNode/Json are both Record<string,unknown>, so no casts). tsc + golden + cross-impl green.
---
