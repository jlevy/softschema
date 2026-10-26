---
type: is
id: is-01m5rz965g7cp8x9knqmftypqz
title: "PR #60 B1: no test checks that _JSON_PATH_ENABLED consults the version gate"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rz94fz61efjcn7fbzfy3nx
hold: null
hold_until: null
created_at: 2026-10-25T07:26:57.711Z
updated_at: 2026-10-25T15:50:30.559Z
started_at: 2026-10-25T07:29:01.352Z
closed_at: 2026-10-25T15:50:30.559Z
close_reason: "fixed in 910e04b: _json_path_enabled(parser_cls, version) pure function; test_the_json_path_gate_needs_the_pure_parser_at_a_checked_release (5 cases) and test_the_gate_is_what_this_process_runs pin both halves of the gate"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/60#pullrequestreview-5641954816. _portable.py:237; test_json_fast_path.py:604-624. Fix (a): pure function _json_path_enabled(parser_cls, version) with tests.
