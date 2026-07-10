---
type: is
id: is-01kt599je84fz7zxjn8fmwxtm9
title: "golden+parity: no cross-impl coverage for error-normalization cases"
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
created_at: 2026-06-02T23:04:27.335Z
updated_at: 2026-07-10T03:49:12.314Z
closed_at: 2026-06-02T23:12:51.298Z
close_reason: "Done: tests/golden/scenarios/error-normalization.md exercises required/multipleOf/type/enum/additionalProperties across both CLIs (byte-identical), plus unit tests in coverage.test.ts."
---
Add golden/parity scenarios that exercise multipleOf, missing-required, envelope_mismatch fields, additionalProperties, and float bounds across both CLIs so these parity gaps cannot silently regress.
