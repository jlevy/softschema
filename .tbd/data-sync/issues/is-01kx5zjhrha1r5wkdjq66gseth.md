---
type: is
id: is-01kx5zjhrha1r5wkdjq66gseth
title: Use Unicode scalar ordering for canonical schema required arrays
kind: bug
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - canonicalization
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:20:55.696Z
updated_at: 2026-07-10T12:36:20.387Z
closed_at: 2026-07-10T12:36:20.386Z
close_reason: TypeScript canonical required-array sorting now uses Unicode scalar ordering; Python, Node, and Bun exact adapters pass all 7 canonicalization cases.
---
TypeScript canonicalization sorts required arrays with UTF-16 ordering, so astral/BMP keys such as U+1F600 and U+E000 produce different canonical bytes and hashes than Python. Use the shared Unicode scalar comparator and add cross-runtime vectors.
