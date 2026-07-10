---
type: is
id: is-01kx4zcarag9errp6pes9b7hwx
title: Define portable JSON Schema regular-expression semantics
kind: bug
status: closed
priority: 1
version: 8
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
  - type: blocks
    target: is-01kx64dj887nrm1d41xspztcqt
  - type: blocks
    target: is-01kx6dmkfg4vcq8nfckm2e21zb
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T02:58:17.481Z
updated_at: 2026-07-10T16:29:08.683Z
closed_at: 2026-07-10T06:40:48.356Z
close_reason: Implemented and verified in 0854bcc
---
Python jsonschema and Ajv execute pattern and patternProperties with different regex engines. Define a machine-readable cross-runtime regex profile or adopt one shared engine, eagerly reject invalid/unsupported expressions with the stable schema_invalid pattern reason, suppress engine warnings, and add Python/Node/Bun differential vectors for syntax and matching semantics.
