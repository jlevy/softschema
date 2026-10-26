---
type: is
id: is-01m5sv1ayqxt1h50bexftbqgcc
title: "PR #64 B4: one explicit trim set for all six fence checks in both runtimes"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T15:32:00.599Z
updated_at: 2026-10-25T16:25:54.888Z
closed_at: 2026-10-25T16:25:54.888Z
close_reason: "Fixed in 04b6c3e (PR #64): is_fence_line/isFenceLine trim only space and tab after a trailing CR in all six fence checks; empty-block check uses the explicit set; spec states the rule; six fence_scan vectors consumed by both runtimes."
resolution: null
duplicate_of: null
---
Medium. validate.py:1080,1082, _portable.py:283,291,320, validate.ts:167,170, portable.ts:282,288,315. rstrip(" \t") / [ \t]+$ + hardening vector.
