---
type: is
id: is-01kx4scdps38egdehmsnnfqynp
title: Make canonicalization and enforced overlays semantics-preserving
kind: bug
status: open
priority: 1
version: 1
labels:
  - parity
  - json-schema
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:29.048Z
updated_at: 2026-07-10T01:13:29.048Z
---
Nullable oneOf rewriting can change validity, recursive schema keyword tables miss draft 2020-12 positions such as dependentSchemas, and closing allOf branches can reject valid composed objects. Constrain the input profile or implement a complete semantics-aware traversal with conformance tests.
