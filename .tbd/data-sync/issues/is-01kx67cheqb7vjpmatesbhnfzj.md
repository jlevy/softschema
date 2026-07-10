---
type: is
id: is-01kx67cheqb7vjpmatesbhnfzj
title: Align YAML property-token error locations
kind: bug
status: closed
priority: 2
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - yaml
  - diagnostics
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T14:37:27.382Z
updated_at: 2026-07-10T18:36:57.496Z
closed_at: 2026-07-10T18:36:57.495Z
close_reason: Aligned YAML property-token diagnostic locations across runtimes.
---
TypeScript reports nonportable custom-tag errors at the scalar or collection token while Python reports the preceding YAML property token. Associate composed values with CST tag offsets and add cross-runtime vectors for scalar, sequence, mapping, and directive-expanded tags.

## Notes

Align custom and malformed built-in tag errors for scalar/sequence/map nodes to the YAML property token, including directive-expanded handles; no parser or BigInt exception may escape.
