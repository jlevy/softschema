---
type: is
id: is-01kx4scd7k1zff7ahr2y6nmrht
title: Define and enforce cross-runtime JSON-compatible YAML and format semantics
kind: bug
status: open
priority: 1
version: 1
labels:
  - parity
  - python
  - typescript
  - spec
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:28.562Z
updated_at: 2026-07-10T01:13:28.562Z
---
Python and TypeScript disagree on JSON Schema format assertions and on YAML timestamps, non-finite values, tags, and unsafe integers. Specify the supported YAML value domain and format assertion set, enforce it at parse and validation boundaries, and add differential fixtures plus a curated JSON Schema Test Suite subset.
