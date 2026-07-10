---
type: is
id: is-01kx4scceq7dvdk8btj7k61rv9
title: Disable remote JSON Schema reference retrieval by default
kind: bug
status: open
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - python
  - parity
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:27.766Z
updated_at: 2026-07-10T01:59:39.984Z
---
Python Draft202012Validator follows unresolved HTTP references and can initiate network requests while validating a schema from an untrusted checkout. Install an explicit no-retrieval registry by default, define trusted opt-in resolution if needed, normalize failures as schema_invalid, and add Python versus TypeScript security tests.
