---
type: is
id: is-01m8cn66q0j9njqwnb1nhrk07c
title: Stream candidate references and build schema catalogs
kind: task
status: open
priority: 2
version: 3
spec_path: docs/softschema-collection-design.md
labels: []
dependencies:
  - type: blocks
    target: is-01m8cn67dkwa0xhbx042ps1d82
  - type: blocks
    target: is-01m8cn67zqgerqe5tabncb4d37
parent_id: is-01m8cn371smmc04w3rptr8rpfs
created_at: 2026-11-26T19:26:46.495Z
updated_at: 2026-11-26T19:26:47.797Z
---
Implement zero-content-open candidate enumeration, terminal scope coverage, schema-first fallback catalogs with opt-in roots/suffixes, and safe explicit pointers. Test large flat directories, cancellation, and incomplete catalog binding in both runtimes.
