---
type: is
id: is-01m5rxgh259tc24z1sj5c9kbvb
title: "PR #64 A10: suggestion: tighten the representer regression test assertion"
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
created_at: 2026-10-25T06:56:01.093Z
updated_at: 2026-10-25T07:12:34.965Z
started_at: 2026-10-25T06:56:43.071Z
closed_at: 2026-10-25T07:12:34.965Z
close_reason: "fixed in ce14939: assertion is type(yaml.representer) is _RoundTripRepresenter; imports hoisted to module top."
resolution: null
duplicate_of: null
---
Suggestion. packages/python/tests/test_repair_conform.py:244: assert type(...) is _RoundTripRepresenter; hoist imports.
PR #64. Review A: https://github.com/jlevy/softschema/pull/64#pullrequestreview-5641911619
