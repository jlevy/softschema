---
type: is
id: is-01m5rz9cnry6wffmc13cp44fc2
title: "PR #62 C5: fuzz harness nits (print versions, partial batch, tiny test)"
kind: task
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rz95cv2g6jbq8knpb9z5t2
hold: null
hold_until: null
created_at: 2026-10-25T07:27:04.375Z
updated_at: 2026-10-25T15:50:33.211Z
started_at: 2026-10-25T07:37:34.725Z
closed_at: 2026-10-25T15:50:33.211Z
close_reason: "fixed in 3d0aa10: fuzz summary prints ruamel/clib/libyaml versions and seeds; partial last batch; --jobs 1 inline; test_the_fuzz_harness_runs_and_finds_no_divergence"
resolution: null
duplicate_of: null
---
Suggestion. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642029532. devtools/yaml_parser_fuzz.py:319,:329-331.
