---
type: is
id: is-01kt599h3c5nv84m6r1xryv4ja
title: 'errors.ts: multipleOf validator_value is undefined (message says \"multiple of None\")'
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
created_at: 2026-06-02T23:04:25.959Z
updated_at: 2026-07-10T03:49:11.763Z
closed_at: 2026-06-02T23:12:50.367Z
close_reason: "Fixed: normalizeAjvError reads error.schema (verbose) for validator_value; multipleOf now carries the divisor. Unit + golden coverage added."
---
validatorValueFor() default branch reads params.limit, but ajv puts the divisor in params.multipleOf. Result: validator_value undefined (dropped by JSON) and message \"value 7 is not a multiple of None\". Python emits validator_value 5 and \"... multiple of 5\". Untested: parity fixture has step multipleOf(5) but no golden exercises it.
