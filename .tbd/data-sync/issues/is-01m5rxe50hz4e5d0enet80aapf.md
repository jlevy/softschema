---
type: is
id: is-01m5rxe50hz4e5d0enet80aapf
title: "PR #59 B2: walk follows contentSchema and then/else without if"
kind: bug
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/done/plan-2026-09-12-validation-execution-evidence.md
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rxe40c2nyv4rwytvha8dhy
hold: null
hold_until: null
created_at: 2026-10-25T06:54:43.217Z
updated_at: 2026-10-26T03:34:07.490Z
started_at: 2026-10-25T06:54:50.125Z
closed_at: 2026-10-25T07:16:43.103Z
close_reason: "fixed in e02b064 (option 1, Ajv reach): walk keyword rule; vectors content-schema-dangling-reference, then-without-if-dangling-reference, then-with-if-dangling-reference; lone if and if-with-empty-then pinned as engine_deviations"
resolution: null
duplicate_of: null
---
Medium. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5641896780. validate.py _SCHEMA_SINGLES reused by walk. Fix option 1: walk-specific reach matching Ajv; pin lone if as engine difference; vectors.
