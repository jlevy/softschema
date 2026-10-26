---
type: is
id: is-01m5rtcjpmkdg0nk4dnxm7w5xd
title: "PR #62 B1: _ROOT_BLOCK_SCALAR backtracks exponentially; validate hangs on a banner comment"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rr5yfcqwbhca5tae5pznyy
hold: null
hold_until: null
created_at: 2026-10-25T06:01:25.972Z
updated_at: 2026-10-25T06:29:32.989Z
started_at: 2026-10-25T06:29:28.094Z
closed_at: 2026-10-25T06:29:32.988Z
close_reason: "fixed in 69dd7e7 (#62): possessive quantifiers in _ROOT_BLOCK_SCALAR; bounded-time tests; banner in C_FIRST; docs"
resolution: null
duplicate_of: null
---
Blocker. PR #62, review B: https://github.com/jlevy/softschema/pull/62#pullrequestreview-5641769416. packages/python/src/softschema/_portable.py:177 (pattern), :237 (call). Nested repetition in the leading-comment scan; a 24-char # banner takes 1.4 s and grows 2x per #. Fix: possessive quantifiers (Python >=3.11), regression tests with bounded time, banner document in C_FIRST, correct docstring and design doc.
