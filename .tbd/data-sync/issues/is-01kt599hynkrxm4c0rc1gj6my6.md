---
type: is
id: is-01kt599hynkrxm4c0rc1gj6my6
title: "errors.ts: additionalProperties emits one record per extra key (ajv) vs one (jsonschema)"
kind: bug
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-06-01-softschema-typescript-zod-parity.md
labels:
  - parity
  - typescript
dependencies: []
parent_id: is-01kt5990p0172ch8443kj99z17
created_at: 2026-06-02T23:04:26.836Z
updated_at: 2026-06-02T23:12:51.119Z
closed_at: 2026-06-02T23:12:51.119Z
close_reason: "Fixed: collapseAdditionalProperties() keeps one record per object path, matching jsonschema's single record. Golden + unit coverage."
---
With additionalProperties:false and multiple extra keys, ajv yields one error per extra property (parent-path value) while jsonschema yields one. Record count and value payloads diverge.
