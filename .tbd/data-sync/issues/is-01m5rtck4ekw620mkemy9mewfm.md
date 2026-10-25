---
type: is
id: is-01m5rtck4ekw620mkemy9mewfm
title: "PR #62 B2: _BLOCK_SPACE_LINE is quadratic in line length"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5rr5yfcqwbhca5tae5pznyy
created_at: 2026-10-25T06:01:26.414Z
updated_at: 2026-10-25T06:01:26.414Z
---
Medium. PR #62, review B: https://github.com/jlevy/softschema/pull/62#pullrequestreview-5641769416. _portable.py:170, called at :231. The search restarts at every | or > and scans to end of line. Fix: find space-only lines first, then test only the preceding line with a bounded pattern; add a linear-cost test.
