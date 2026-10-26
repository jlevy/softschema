---
type: is
id: is-01m5rz9dx77h0rksee4pa9stkh
title: "PR #62 C7: nothing exercises C-first off Linux"
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
created_at: 2026-10-25T07:27:05.639Z
updated_at: 2026-10-25T15:50:33.757Z
started_at: 2026-10-25T07:37:35.486Z
closed_at: 2026-10-25T15:50:33.757Z
close_reason: "fixed in 3d0aa10: every Artifact smoke job (ubuntu/macOS/Windows) runs the wheel with ruamel.yaml.clib and asserts c-first (6/6 green in run 40175647375); _ruamel_yaml module fallback in the gate with a test"
resolution: null
duplicate_of: null
---
Suggestion. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642029532. Add a smoke step installing ruamel.yaml.clib and asserting c-first on macOS/Windows; fall back to sys.modules.get('_ruamel_yaml') in the gate.
