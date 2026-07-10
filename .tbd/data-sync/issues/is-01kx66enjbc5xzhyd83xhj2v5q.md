---
type: is
id: is-01kx66enjbc5xzhyd83xhj2v5q
title: Make source-resource tests installation-mode independent
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - testing
  - packaging
  - python
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T14:21:08.554Z
updated_at: 2026-07-10T14:22:20.687Z
closed_at: 2026-07-10T14:22:20.686Z
close_reason: Source-resource trust test now passes deterministically under wheel-first CI and source runs.
---
The exact-source-checkout resource test relies on whichever softschema installation happens to be imported. It passes under an editable source install but fails after CI correctly installs the built wheel, even though installed behavior is correct. Bind the test explicitly to the source module path so both wheel-first CI and source runs verify the intended trust decision.

## Notes

Explicitly bound the source-checkout test to packages/python/src/softschema/cli.py while keeping importlib.resources pointed at stale bundled content, so the test now exercises the intended exact-layout decision under either an installed wheel or source environment. Evidence: focused 24 tests passed; Ruff and basedpyright clean; hash-constrained wheel verified 53 installed files including _bounded_file.py; full wheel-first suite 662 passed.
