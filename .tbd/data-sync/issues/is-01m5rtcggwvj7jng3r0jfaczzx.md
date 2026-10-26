---
type: is
id: is-01m5rtcggwvj7jng3r0jfaczzx
title: "PR #60 A1: test_json_fast_path.py makes the default pytest suite 4x slower"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rr5y30vn078tgerprth9hg
hold: null
hold_until: null
created_at: 2026-10-25T06:01:23.739Z
updated_at: 2026-10-25T06:29:31.174Z
started_at: 2026-10-25T06:01:45.125Z
closed_at: 2026-10-25T06:29:31.174Z
close_reason: "fixed in c447283 (#60): slow marker tier excluded by addopts, CI step runs it; default suite 23 s -> 7 s"
resolution: null
duplicate_of: null
---
Medium. PR #60, review A: https://github.com/jlevy/softschema/pull/60#pullrequestreview-5641761087. packages/python/tests/test_json_fast_path.py:272,:419-422,:445-461,:465. Corpus, generated, sampled and deep tests add ~18 s to the default run. Fix: slow marker tier excluded by default plus a CI step that runs it.
