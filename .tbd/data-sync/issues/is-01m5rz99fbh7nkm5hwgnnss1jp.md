---
type: is
id: is-01m5rz99fbh7nkm5hwgnnss1jp
title: "PR #60 D3: pin the tab-in-flow rule the JSON path relies on"
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
created_at: 2026-10-25T07:27:01.099Z
updated_at: 2026-10-25T15:50:32.098Z
started_at: 2026-10-25T07:29:03.459Z
closed_at: 2026-10-25T15:50:32.098Z
close_reason: "fixed in 910e04b on #60 (owning layer): comment at _JSON_ROOT names scan_to_next_token's flow-level tab rule; test_tabs_between_flow_tokens_are_whitespace_to_ruamel pins six tab-in-flow texts"
resolution: null
duplicate_of: null
---
Low, owning layer #60. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642060738. _portable.py _JSON_ROOT: comment pointing at ruamel scan_to_next_token; named pinned case with a tab at the start of a line inside the root collection.
