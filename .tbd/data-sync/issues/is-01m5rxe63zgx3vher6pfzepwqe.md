---
type: is
id: is-01m5rxe63zgx3vher6pfzepwqe
title: "PR #59 B4: $dynamicRef with no anchor diverges (TS untyped root valid, Python errored) and is unpinned"
kind: bug
status: closed
priority: 3
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rxe40c2nyv4rwytvha8dhy
hold: null
hold_until: null
created_at: 2026-10-25T06:54:44.350Z
updated_at: 2026-10-25T07:16:44.169Z
started_at: 2026-10-25T06:54:51.337Z
closed_at: 2026-10-25T07:16:44.169Z
close_reason: "fixed in e02b064 (pinned): engine_deviations dynamic-ref-missing-anchor-typed-root/-untyped-root, root-dynamic-reference; spec lists it (11f2d34)"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5641896780. Pre-existing. Fix: pin as engine deviation vector + spec sentence, or refuse in both.
