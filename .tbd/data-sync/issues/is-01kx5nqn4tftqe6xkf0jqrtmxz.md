---
type: is
id: is-01kx5nqn4tftqe6xkf0jqrtmxz
title: Reject legacy YAML line-separator spellings consistently
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - yaml
  - diagnostics
dependencies:
  - type: blocks
    target: is-01kx4vfebyfym3whq7f3e3x0qs
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T09:28:57.241Z
updated_at: 2026-07-10T09:47:18.586Z
closed_at: 2026-07-10T09:47:18.585Z
close_reason: Implemented and verified in both runtimes with shared parser/location/CLI and conformance vectors.
---
Python/ruamel and TypeScript/yaml interpret literal U+0085, U+2028, and U+2029 differently in YAML scalars, and the TypeScript source map incorrectly counts them as line breaks. Define a conservative portable-source rule that rejects the three literal legacy separator code points before parsing (while allowing escaped Unicode values in double-quoted scalars), count only CR/LF/CRLF as source line breaks, add shared value/location/CLI vectors, and include the rule in the spec and conformance kit.

## Notes

Implemented pre-parse rejection of literal U+0085/U+2028/U+2029 in Python and TypeScript with shared exact-location and CLI vectors; escaped double-quoted forms remain accepted; SourceText now recognizes only CR/LF/CRLF. Spec and conformance portable-yaml vectors include the rule. Verified 53 focused Python tests, 497 TypeScript tests, build/typecheck/publint, and cross-implementation byte parity.
