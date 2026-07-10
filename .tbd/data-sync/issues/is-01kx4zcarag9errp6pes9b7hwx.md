---
type: is
id: is-01kx4zcarag9errp6pes9b7hwx
title: Define portable JSON Schema regular-expression semantics
kind: bug
status: open
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - json-schema
dependencies:
  - type: blocks
    target: is-01kx4vfekaj195cy4tav9nrwgg
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T02:58:17.481Z
updated_at: 2026-07-10T03:02:17.783Z
---
Python jsonschema and Ajv execute pattern and patternProperties with different regex engines. Define a machine-readable cross-runtime regex profile or adopt one shared engine, eagerly reject invalid/unsupported expressions with the stable schema_invalid pattern reason, suppress engine warnings, and add Python/Node/Bun differential vectors for syntax and matching semantics.
