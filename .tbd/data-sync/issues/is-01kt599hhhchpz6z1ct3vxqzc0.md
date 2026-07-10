---
type: is
id: is-01kt599hhhchpz6z1ct3vxqzc0
title: "errors.ts: required validator_value diverges (single key vs full required list)"
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/done/plan-2026-06-01-softschema-typescript-zod-parity.md
labels:
  - parity
  - typescript
dependencies: []
parent_id: is-01kt5990p0172ch8443kj99z17
created_at: 2026-06-02T23:04:26.416Z
updated_at: 2026-07-10T03:49:12.131Z
closed_at: 2026-06-02T23:12:50.746Z
close_reason: "Fixed: validator_value now comes from error.schema = full required list, matching jsonschema (one record per missing key). Golden + unit coverage added."
---
Python sets validator_value to the full required array (jsonschema error.validator_value) -> message \"required property [..] is missing\"; TS uses params.missingProperty (single key). TS must mirror Python (the published reference). Untested: bad-movie.md golden has all required fields.
