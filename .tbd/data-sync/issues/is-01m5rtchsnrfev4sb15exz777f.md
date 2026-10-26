---
type: is
id: is-01m5rtchsnrfev4sb15exz777f
title: "PR #60 A4: nothing gates the JSON path on the ruamel versions its guards were derived from"
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
created_at: 2026-10-25T06:01:25.045Z
updated_at: 2026-10-25T06:29:32.250Z
started_at: 2026-10-25T06:01:46.125Z
closed_at: 2026-10-25T06:29:32.250Z
close_reason: "fixed in c447283 (#60): CHECKED_RUAMEL_VERSIONS gate with tests; same approach gates C-first in #62 (69dd7e7)"
resolution: null
duplicate_of: null
---
Low. PR #60, review A: https://github.com/jlevy/softschema/pull/60#pullrequestreview-5641761087. _portable.py:218; pyproject.toml:25. Fix: gate _JSON_PATH_ENABLED on the checked ruamel range with a test that the gate turns off outside it (same approach as #62 B3).
