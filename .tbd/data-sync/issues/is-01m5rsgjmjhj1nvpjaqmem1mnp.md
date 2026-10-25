---
type: is
id: is-01m5rsgjmjhj1nvpjaqmem1mnp
title: "PR #59 A2: require mishandles bare string and None/null; runtimes disagree on None"
kind: bug
status: closed
priority: 3
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rr5w4r03h667rqqwvz0a5s
hold: null
hold_until: null
created_at: 2026-10-25T05:46:08.402Z
updated_at: 2026-10-25T06:13:11.570Z
started_at: 2026-10-25T05:46:16.942Z
closed_at: 2026-10-25T06:13:11.570Z
close_reason: "fixed in 5b06690: both runtimes raise TypeError for a bare string, None/null, or non-string elements with one message pointing at [\"structural\"]; unknown names stay ValueError/Error; tests test_require_rejects_bare_string_and_none and the TS 'require rejects a bare string, null, and an unknown layer' test; spec sentence added"
resolution: null
duplicate_of: null
---
Severity: Low. PR #59. Review A: https://github.com/jlevy/softschema/pull/59#pullrequestreview-5641723707. Refs: packages/python/src/softschema/validate.py:122-128, packages/typescript/src/validate.ts:569-576. Fix: reject str/string and None/null and unknown names with the same clear caller error in both runtimes; add tests in both.
