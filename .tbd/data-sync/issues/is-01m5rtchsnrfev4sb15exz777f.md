---
type: is
id: is-01m5rtchsnrfev4sb15exz777f
title: "PR #60 A4: nothing gates the JSON path on the ruamel versions its guards were derived from"
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
created_at: 2026-10-25T06:01:25.045Z
updated_at: 2026-10-25T06:01:46.126Z
started_at: 2026-10-25T06:01:46.125Z
---
Low. PR #60, review A: https://github.com/jlevy/softschema/pull/60#pullrequestreview-5641761087. _portable.py:218; pyproject.toml:25. Fix: gate _JSON_PATH_ENABLED on the checked ruamel range with a test that the gate turns off outside it (same approach as #62 B3).
