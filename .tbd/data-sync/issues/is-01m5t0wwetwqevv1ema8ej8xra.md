---
type: is
id: is-01m5t0wwetwqevv1ema8ej8xra
title: "PR #60 C2: 'five tests that prove a JSON document never reaches ruamel' counts two that prove something else"
kind: task
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0wve6ey9s4t2vyxfwmgh5
created_at: 2026-10-25T17:14:26.138Z
updated_at: 2026-10-25T17:20:36.530Z
closed_at: 2026-10-25T17:20:36.530Z
close_reason: "fixed in 6b216e8: docstring and installed-release test say 'five tests that need the path (three prove a JSON document never reaches ruamel; two are the slow comparisons)'; PR body B2 sentence and Not Verified note match"
resolution: null
duplicate_of: null
---
Low suggestion. test_json_fast_path.py:40-43, :665 and the PR body B2 sentence: three tests prove no ruamel YAML is built; the other two are the slow corpus/generated comparisons. Review https://github.com/jlevy/softschema/pull/60#pullrequestreview-5644279768
