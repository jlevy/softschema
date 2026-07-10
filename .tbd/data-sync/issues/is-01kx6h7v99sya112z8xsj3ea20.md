---
type: is
id: is-01kx6h7v99sya112z8xsj3ea20
title: Bound skill-installer target and recovery-file inspection
kind: bug
status: closed
priority: 2
version: 6
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - skills
  - parity
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T17:29:39.368Z
updated_at: 2026-07-10T18:36:58.170Z
closed_at: 2026-07-10T18:36:58.169Z
close_reason: Bound skill target, residue, and lock inspection with non-mutating conflict behavior.
---
Both installers read existing target, stage, and backup files without a byte ceiling after a racy stat. A hostile project target or stale residue can force unbounded allocation during dry-run or install. Define a shared maximum managed-skill size, inspect through limit-plus-one regular-file reads in Python and TypeScript, classify oversized or replaced nodes as non-mutating conflicts, and add parity tests.

## Notes

Final integration audit found the pre-existing installer lock was still read without a byte ceiling; close only after paired bounded lock-read regressions pass.
