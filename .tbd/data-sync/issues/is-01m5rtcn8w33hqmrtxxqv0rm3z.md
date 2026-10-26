---
type: is
id: is-01m5rtcn8w33hqmrtxxqv0rm3z
title: "PR #62 B7: commit the differential search harness"
kind: task
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rr5yfcqwbhca5tae5pznyy
hold: null
hold_until: null
created_at: 2026-10-25T06:01:28.603Z
updated_at: 2026-10-25T06:29:34.723Z
started_at: 2026-10-25T06:29:29.952Z
closed_at: 2026-10-25T06:29:34.723Z
close_reason: "fixed in 69dd7e7 (#62): devtools/yaml_parser_fuzz.py committed; 100k run, 0 divergences"
resolution: null
duplicate_of: null
---
Suggestion. PR #62, review B: https://github.com/jlevy/softschema/pull/62#pullrequestreview-5641769416. Put the C-vs-pure differential generator and comparison under devtools/ so the search can be rerun after a ruamel or clib bump.
