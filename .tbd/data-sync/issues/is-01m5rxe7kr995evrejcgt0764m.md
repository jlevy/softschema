---
type: is
id: is-01m5rxe7kr995evrejcgt0764m
title: "PR #59 C1: no Python test for execution errored and errored+require"
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
created_at: 2026-10-25T06:54:45.880Z
updated_at: 2026-10-26T03:34:07.490Z
started_at: 2026-10-25T06:54:50.948Z
closed_at: 2026-10-25T07:16:45.717Z
close_reason: "fixed in e02b064: test_structural_errored_when_evaluation_raises (errored, schema_invalid, check_not_completed(errored))"
resolution: null
duplicate_of: null
---
Medium. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5641920187. test_enforcement_clarity.py. Fix: unit test with Mapping subclass raising during properties evaluation; assert errored, schema_invalid, check_not_completed(errored).
