---
type: is
id: is-01kt599hr2t3y2mvy1kq5wg9m6
title: "errors.ts: type validator_value is a joined string for multi-type schemas"
kind: bug
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/done/plan-2026-06-01-softschema-typescript-zod-parity.md
labels:
  - parity
  - typescript
dependencies: []
parent_id: is-01kt5990p0172ch8443kj99z17
created_at: 2026-06-02T23:04:26.625Z
updated_at: 2026-07-10T03:49:12.498Z
closed_at: 2026-06-02T23:12:50.931Z
close_reason: "Fixed: type validator_value now reads error.schema (exact type value), correct for single- and multi-type."
---
ajv params.type is a comma-joined string for [\"string\",\"null\"]; Python validator_value is the list. Diverges for multi-type type errors. Rare given canonical profile collapses nullable to anyOf, but real.
