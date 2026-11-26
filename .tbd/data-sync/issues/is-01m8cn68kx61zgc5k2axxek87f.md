---
type: is
id: is-01m8cn68kx61zgc5k2axxek87f
title: Benchmark portable native JSON and header-only parsing
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
created_at: 2026-11-26T19:26:48.444Z
updated_at: 2026-11-26T19:26:49.177Z
---
Measure native JSON and frontmatter fast paths for the same semantics using duplicate keys, escape, limit and decoded-value parity vectors. Use Universe and a generated JSON/large-body corpus. Keep guarded fallbacks for unsupported shapes.
