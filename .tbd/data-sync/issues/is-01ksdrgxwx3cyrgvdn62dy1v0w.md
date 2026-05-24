---
type: is
id: is-01ksdrgxwx3cyrgvdn62dy1v0w
title: Require validation implementation in CLI validate
kind: task
status: closed
priority: 3
version: 2
labels: []
dependencies: []
created_at: 2026-05-24T19:48:50.717Z
updated_at: 2026-05-24T19:48:54.957Z
closed_at: 2026-05-24T19:48:54.956Z
close_reason: softschema validate now requires --model or --schema and has CLI coverage.
---
Make softschema validate fail fast unless the caller supplies a model, schema sidecar, or both, so document metadata is not mistaken for executable validation.
