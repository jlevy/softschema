---
type: is
id: is-01kx4scdf1nc4691pt20msnpm0
title: Validate contract IDs at every API and CLI boundary
kind: bug
status: open
priority: 2
version: 10
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - python
  - typescript
  - spec
dependencies:
  - type: blocks
    target: is-01kx4vfekaj195cy4tav9nrwgg
  - type: blocks
    target: is-01kx4scdycksywq351ypme5nf8
  - type: blocks
    target: is-01kx4vfdwqtmk0tt9q9kznyhwq
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
  - type: blocks
    target: is-01kx4w3naff8dxxw9bq9bfz1c9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:28.801Z
updated_at: 2026-07-10T02:15:27.003Z
---
Use one validated ContractId abstraction at metadata, API, registry, CLI, and compiler boundaries. Stop deriving JSON Schema $id from logical contract IDs; add canonical absolute schema URIs with no non-empty fragment and one explicit compiler option; regenerate both outputs and hashes once.
