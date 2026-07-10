---
type: is
id: is-01kx4scczp99jp7ztfmcjqrfb7
title: Return structured schema_invalid results for every malformed compiled schema
kind: bug
status: open
priority: 1
version: 1
labels:
  - python
  - typescript
  - parity
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:28.308Z
updated_at: 2026-07-10T01:13:28.308Z
---
Non-mapping roots and invalid JSON Schema keyword values currently produce Python tracebacks or TypeScript usage errors instead of the normative structured schema_invalid result. Centralize schema loading, validate against the metaschema, normalize reference and compile failures, and add shared golden cases.
