---
type: is
id: is-01m5rz9atkfp0e41ndae0y92r6
title: "PR #62 C2: guard-cost tests cannot detect a quadratic"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rz95cv2g6jbq8knpb9z5t2
hold: null
hold_until: null
created_at: 2026-10-25T07:27:02.483Z
updated_at: 2026-10-25T15:50:32.684Z
started_at: 2026-10-25T07:37:33.642Z
closed_at: 2026-10-25T15:50:32.683Z
close_reason: "fixed in 3d0aa10: 3 new adversarial inputs (100k space lines after emoji, 50k indented blank lines, 50k CR-only), growth test parametrized over 7 shapes at 20k vs 200k, best of 3, bound < 30x"
resolution: null
duplicate_of: null
---
Medium. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642029532 ; also D1. test_c_parser.py:538,:590-601. Add emoji-prefixed 100k space-line input (expected False), no-header space-line shapes incl. CR-only, measure 20k vs 200k with warm-up/best-of-N and require <30x.
