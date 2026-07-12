---
type: is
id: is-01kxa51yxnbsd4ywnzde4f43rz
title: "PR21 R1: preserve indented frontmatter delimiters"
kind: bug
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01kxa51ypp776456nxmyd81gps
created_at: 2026-07-12T03:13:41.300Z
updated_at: 2026-07-12T03:27:21.307Z
closed_at: 2026-07-12T03:27:21.307Z
close_reason: Frontmatter delimiters now require column one; the shared block-scalar case preserves indented --- and following fields in both runtimes.
---
Fix frontmatter splitting so only an unindented closing delimiter ends the block; add shared coverage for an indented delimiter inside a block scalar.
