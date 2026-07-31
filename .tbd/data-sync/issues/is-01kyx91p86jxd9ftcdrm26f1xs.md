---
type: is
id: is-01kyx91p86jxd9ftcdrm26f1xs
title: Implement scoped Python timestamp-string decoding
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-31-portable-yaml-timestamps.md
labels:
  - github-22
  - python
dependencies:
  - type: blocks
    target: is-01kyx92qar1jne3qgxgk8hnn90
parent_id: is-01kyx90yh6vv5n0jdmhh5dar9n
created_at: 2026-07-31T23:44:42.757Z
updated_at: 2026-07-31T23:46:56.242Z
closed_at: 2026-07-31T23:46:56.241Z
close_reason: "Both runtime beads are implemented and their focused regressions pass: Python retains scoped constructor isolation and TypeScript retains string parsing while rejecting host-native Date metadata."
---
Replace lexical timestamp rejection with a private SafeConstructor subclass that converts the implicit YAML timestamp tag to node.value. Assign it per parser instance, retain the constructed-value guard for host-native date/datetime inputs, and use an accurate portable-value error. Acceptance: lexical spelling and precision are preserved, explicit tags remain rejected, semantic Pydantic date/datetime validation accepts valid strings and rejects invalid strings, and fresh unrelated ruamel.yaml instances behave identically before and after softschema parsing.

## Notes

Python implementation and focused regression coverage are present; verifying constructor isolation and semantic model behavior before closure.
