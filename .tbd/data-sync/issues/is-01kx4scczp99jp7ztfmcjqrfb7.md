---
type: is
id: is-01kx4scczp99jp7ztfmcjqrfb7
title: Return structured schema_invalid results for every malformed compiled schema
kind: bug
status: open
priority: 1
version: 13
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - python
  - typescript
  - parity
dependencies:
  - type: blocks
    target: is-01kx4scceq7dvdk8btj7k61rv9
  - type: blocks
    target: is-01kx4scd7k1zff7ahr2y6nmrht
  - type: blocks
    target: is-01kx4scdps38egdehmsnnfqynp
  - type: blocks
    target: is-01kx4vfekaj195cy4tav9nrwgg
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx4zcarag9errp6pes9b7hwx
  - type: blocks
    target: is-01kx50evvgsk1fep50sk4y6za9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:28.308Z
updated_at: 2026-07-10T03:21:30.263Z
---
Centralize root/supplied-resource schema loading behind stable schema_invalid records, normalize engine compile exceptions, dialect/metaschema/reference failures, preserve legacy-0.2 identity compatibility, reserve pattern for later portable semantics, return exit 1 without engine prose/tracebacks, and keep trusted semantic validation independent.
