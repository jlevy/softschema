---
type: is
id: is-01m5rz9a5wz4yvya0z6wx68ydk
title: "PR #62 C1/D1: _block_scalar_before_space_line rescans the text per space-only line (quadratic)"
kind: bug
status: closed
priority: 1
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rz95cv2g6jbq8knpb9z5t2
hold: null
hold_until: null
created_at: 2026-10-25T07:27:01.819Z
updated_at: 2026-10-25T15:50:32.394Z
started_at: 2026-10-25T07:37:33.083Z
closed_at: 2026-10-25T15:50:32.394Z
close_reason: "fixed in 3d0aa10: both rfind calls bounded by the previous match's start (low = line_end); guard_cost.py 8-14x per 10x on 13 shapes; 3.6M-char emoji doc c-first 0.27 s vs pure 3.70 s (was 23.2 vs 4.4); docstrings, design doc and PR body reworded"
resolution: null
duplicate_of: null
---
High (C1) / Medium (D1). https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642029532 ; https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642060738. _portable.py:238-249 (:246). Fix: bound both rfind calls by the previous match end; reword linear claims in docstring, design doc, PR body.
