---
type: is
id: is-01m8cn67zqgerqe5tabncb4d37
title: Reconcile collection observations without retaining payloads
kind: task
status: open
priority: 2
version: 2
spec_path: docs/softschema-collection-design.md
labels: []
dependencies:
  - type: blocks
    target: is-01m8cn69av6p2n80m3gxvz04st
parent_id: is-01m8cn371smmc04w3rptr8rpfs
created_at: 2026-11-26T19:26:47.797Z
updated_at: 2026-11-26T19:26:49.177Z
---
Separate scan coverage from staged state and remove prior paths only after successful coverage. Support scope and schema invalidation, per-path revision comparison and parity between eager and streaming results.
