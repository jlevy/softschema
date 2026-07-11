---
type: is
id: is-01kx61kkznyp5d0pn9whrd28pr
title: Validate operation-specific standalone adapter requests
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - conformance
  - security
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4w3nqewdhf1d3g0xgvj4ra
  - type: blocks
    target: is-01kx7s4hfwaw78r56phwekh5qs
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:56:27.892Z
updated_at: 2026-07-11T05:08:08.026Z
closed_at: 2026-07-10T13:06:10.537Z
close_reason: Implemented and independently verified strict operation-specific adapter validation with shared no-traceback regressions and all-runtime conformance.
---
Python and JavaScript standalone conformance adapters validate only the generic request envelope, so malformed operation inputs reach KeyError/TypeError tracebacks with nonportable exit 1. Enforce the exact operation-specific input contract, primitive/limit/source-pointer types, and stable exit-2 one-line errors in both adapters with shared hostile regressions.

## Notes

Both standalone adapters now enforce exact operation-specific request/input shapes for all seven operations, including closed safe-integer limits and non-empty unique source-pointer arrays. Shared malformed requests prove exit 2, empty stdout, and one exact stderr line in Python and Bun. Verification: focused Python 3 passed; Bun adapter 3 passed/66 assertions; full Python/Node/Bun conformance 25 artifact cases and 77 vectors.
