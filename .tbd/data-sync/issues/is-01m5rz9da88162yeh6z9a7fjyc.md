---
type: is
id: is-01m5rz9da88162yeh6z9a7fjyc
title: "PR #62 C6: doctor should say why the parser is pure"
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
created_at: 2026-10-25T07:27:05.031Z
updated_at: 2026-10-25T15:50:33.479Z
started_at: 2026-10-25T07:37:35.112Z
closed_at: 2026-10-25T15:50:33.479Z
close_reason: "fixed in 3d0aa10: yaml_parser_reason(); doctor prints it in text and as yaml_parser_reason in --json; pinned by test_the_reason_names_why_the_parser_is_pure and CLI tests"
resolution: null
duplicate_of: null
---
Suggestion. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642029532. cli.py:818. Add a reason / libyaml version field.
