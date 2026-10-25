---
type: is
id: is-01m5rtcggwvj7jng3r0jfaczzx
title: "PR #60 A1: test_json_fast_path.py makes the default pytest suite 4x slower"
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
created_at: 2026-10-25T06:01:23.739Z
updated_at: 2026-10-25T06:01:45.126Z
started_at: 2026-10-25T06:01:45.125Z
---
Medium. PR #60, review A: https://github.com/jlevy/softschema/pull/60#pullrequestreview-5641761087. packages/python/tests/test_json_fast_path.py:272,:419-422,:445-461,:465. Corpus, generated, sampled and deep tests add ~18 s to the default run. Fix: slow marker tier excluded by default plus a CI step that runs it.
