---
type: is
id: is-01m5rtcmc39xmkdsmt02bsxf1n
title: "PR #62 B5: required typescript check fails at bun audit on both layers"
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
created_at: 2026-10-25T06:01:27.682Z
updated_at: 2026-10-25T06:37:56.186Z
started_at: 2026-10-25T06:29:30.793Z
closed_at: 2026-10-25T06:37:56.186Z
close_reason: "deferred: bun audit failure is fixed on PR #64 (claude/zealous-dijkstra-q5g6w0); follow-up tracked in ss-1z8z; stack syncs onto main after #64 merges"
resolution: null
duplicate_of: null
---
Medium, stack-level. PR #62, review B: https://github.com/jlevy/softschema/pull/62#pullrequestreview-5641769416. CI job typescript, step Audit dependencies, runs 40164983295 (#62) and 40098772718 (#60). Owned by PR #64 (claude/zealous-dijkstra-q5g6w0), which merges to main first; follow-up tracked in ss-1z8z.
