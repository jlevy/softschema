---
type: is
id: is-01kx63zq6fyvzrn9y5ctnbx68h
title: Keep frozen candidate verification non-mutating
kind: bug
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - testing
  - security
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
  - type: blocks
    target: is-01kx670z3q4dppv2xp9s7n38e1
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T13:38:01.549Z
updated_at: 2026-07-10T14:31:19.715Z
closed_at: 2026-07-10T13:43:14.531Z
close_reason: Fixed downloaded-candidate self-mutation and verified locally across supported Python lines; ready for the rerun PR matrix.
---
The downloaded frozen-artifact verifier imports candidate-local Python helpers before verifying SHA256SUMS. Default bytecode generation creates devtools/__pycache__ inside the candidate, so the exact inventory rejects its own mutation on every supported OS/runtime. Disable bytecode writes before candidate-local imports, preserve exact unexpected-file rejection, and add a subprocess regression that verifies a freshly transferred candidate without PYTHONDONTWRITEBYTECODE.

## Notes

Implemented temporary pre-import sys.dont_write_bytecode suppression with exact prior-state restoration; exact candidate inventory rejection remains unchanged. Added a fresh transferred-candidate subprocess regression with PYTHONDONTWRITEBYTECODE and PYTHONPYCACHEPREFIX removed. Evidence: focused 3 tests passed; repository lint (Ruff, format, basedpyright, codespell, doc footers) passed; full Python suite 657 passed; full TypeScript gate 534 passed/2069 assertions at 96.20% function and 97.84% line coverage; exact copied verifier passed under CPython 3.11.15 and 3.14.6 with no bytecode nodes. Independent runtime/security review approved the ordering, restoration, cross-platform behavior, and regression.
