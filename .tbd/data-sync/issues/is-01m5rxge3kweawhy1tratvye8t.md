---
type: is
id: is-01m5rxge3kweawhy1tratvye8t
title: "PR #64 A4: repair without --contract reports invalid_utf8 kind / invalid outcome for a non-UTF-8 artifact"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rxgc8kdy9fz5wgg3ew5vsq
hold: null
hold_until: null
created_at: 2026-10-25T06:55:58.066Z
updated_at: 2026-10-25T07:12:35.772Z
started_at: 2026-10-25T07:02:48.972Z
closed_at: 2026-10-25T07:12:35.771Z
close_reason: "fixed in eadf5df: portable_artifact_kind / portableArtifactKind applied to repair's error code in both CLIs; TS unreadableArtifactResult derives outcome via outcomeFor. Tests: test_repair_reports_a_non_utf8_artifact_as_the_same_input_error_validation_does, TS 'repair reports a non-UTF-8 artifact...', golden journey on tests/golden/fixtures/repair-non-utf8.md."
resolution: null
duplicate_of: null
---
Medium, pre-existing. packages/python/src/softschema/cli.py:517-527, packages/typescript/src/cli.ts:761-765. Map repair error code through the validation code-to-kind rule; golden for repair --check on a non-UTF-8 fixture.
PR #64. Review A: https://github.com/jlevy/softschema/pull/64#pullrequestreview-5641911619
