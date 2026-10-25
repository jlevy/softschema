---
type: is
id: is-01m5rtcgxrj5wf050vavr3v7md
title: "PR #60 A2: repo-walk corpus reads untracked and ignored files"
kind: bug
status: in_progress
priority: 2
version: 2
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rr5y30vn078tgerprth9hg
hold: null
hold_until: null
created_at: 2026-10-25T06:01:24.151Z
updated_at: 2026-10-25T06:01:45.468Z
started_at: 2026-10-25T06:01:45.468Z
---
Low. PR #60, review A: https://github.com/jlevy/softschema/pull/60#pullrequestreview-5641761087. test_json_fast_path.py:33,:237-258,:285. _repo_files walks the working tree with os.walk; untracked .tbd/docs and caches dominate the corpus. Fix: enumerate from git ls-files.
