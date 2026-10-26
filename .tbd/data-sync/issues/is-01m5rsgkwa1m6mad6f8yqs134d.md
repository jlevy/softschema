---
type: is
id: is-01m5rsgkwa1m6mad6f8yqs134d
title: "PR #59 A5: SemanticResult.errors can mix kind-keyed and issue-shaped records"
kind: bug
status: closed
priority: 3
version: 4
spec_path: docs/project/specs/done/plan-2026-09-12-validation-execution-evidence.md
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rr5w4r03h667rqqwvz0a5s
hold: null
hold_until: null
created_at: 2026-10-25T05:46:09.674Z
updated_at: 2026-10-26T03:34:06.199Z
started_at: 2026-10-25T05:46:17.977Z
closed_at: 2026-10-25T06:13:12.578Z
close_reason: "fixed in 39eac06 (documented): spec Required checks says the appended record is kind-keyed while completed semantic errors are the validator's own issue records with no kind, so consumers of semantic.errors dispatch on kind first"
resolution: null
duplicate_of: null
---
Severity: Low (suggestion, preference). PR #59. Review A: https://github.com/jlevy/softschema/pull/59#pullrequestreview-5641723707. Refs: packages/python/src/softschema/validate.py:149-154,509. Fix: document in spec that consumers dispatch on kind before reading issue fields, or decline as intended.
