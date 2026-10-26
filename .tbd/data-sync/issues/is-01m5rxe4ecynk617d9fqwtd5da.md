---
type: is
id: is-01m5rxe4ecynk617d9fqwtd5da
title: "PR #59 B1: reference walk re-enters a lookup target's $id (dir/dir double-join) and refuses valid schemas"
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/done/plan-2026-09-12-validation-execution-evidence.md
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rxe40c2nyv4rwytvha8dhy
hold: null
hold_until: null
created_at: 2026-10-25T06:54:42.636Z
updated_at: 2026-10-26T03:34:07.490Z
started_at: 2026-10-25T06:54:49.740Z
closed_at: 2026-10-25T07:16:42.562Z
close_reason: "fixed in e02b064: entered flag in _check_references; vectors nested-relative-id-reference-reached/-unreached/-rejects, embedded-id-resource-internal-reference; also Qodo 3"
resolution: null
duplicate_of: null
---
High. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5641896780 (= Qodo 3 ). validate.py _check_references: in_subresource called on lookup() results. Fix: entered flag; vectors for reached/unreached B1 shape and structurally embedded $id (C4).
