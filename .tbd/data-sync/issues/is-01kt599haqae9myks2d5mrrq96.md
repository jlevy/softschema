---
type: is
id: is-01kt599haqae9myks2d5mrrq96
title: "validate.ts: envelope_mismatch record drops expected_key/actual_keys"
kind: bug
status: closed
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-06-01-softschema-typescript-zod-parity.md
labels:
  - parity
  - typescript
dependencies: []
parent_id: is-01kt5990p0172ch8443kj99z17
created_at: 2026-06-02T23:04:26.198Z
updated_at: 2026-06-02T23:12:50.564Z
closed_at: 2026-06-02T23:12:50.563Z
close_reason: "Fixed: envelope_mismatch failure now passes expected_key/actual_keys, matching Python validate.py."
---
TS failure() for envelope_mismatch passes no extra, so the record lacks expected_key and actual_keys that Python validate.py includes. Non-identical structural JSON for the same failing document.
