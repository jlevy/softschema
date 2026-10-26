---
type: is
id: is-01m5rz96tbn429wtsv85gm26w0
title: "PR #60 B2: C-extension half of the gate can turn the JSON path off with a green suite"
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
created_at: 2026-10-25T07:26:58.379Z
updated_at: 2026-10-25T15:50:30.839Z
started_at: 2026-10-25T07:29:01.825Z
closed_at: 2026-10-25T15:50:30.838Z
close_reason: "fixed in 910e04b: CI build job sets SOFTSCHEMA_REQUIRE_JSON_PATH=1; requires_json_path no longer skips under it and test_installed_ruamel_is_a_checked_release asserts _JSON_PATH_ENABLED; CI run 40173172789 green"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/60#pullrequestreview-5641954816. test_json_fast_path.py:37-40,:541-566,:622-624. Fix: SOFTSCHEMA_REQUIRE_JSON_PATH=1 in CI build job; under it the path must be enabled and requires_json_path fails instead of skipping.
