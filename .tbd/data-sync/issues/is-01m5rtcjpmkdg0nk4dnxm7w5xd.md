---
type: is
id: is-01m5rtcjpmkdg0nk4dnxm7w5xd
title: "PR #62 B1: _ROOT_BLOCK_SCALAR backtracks exponentially; validate hangs on a banner comment"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5rr5yfcqwbhca5tae5pznyy
created_at: 2026-10-25T06:01:25.972Z
updated_at: 2026-10-25T06:01:25.972Z
---
Blocker. PR #62, review B: https://github.com/jlevy/softschema/pull/62#pullrequestreview-5641769416. packages/python/src/softschema/_portable.py:177 (pattern), :237 (call). Nested repetition in the leading-comment scan; a 24-char # banner takes 1.4 s and grows 2x per #. Fix: possessive quantifiers (Python >=3.11), regression tests with bounded time, banner document in C_FIRST, correct docstring and design doc.
