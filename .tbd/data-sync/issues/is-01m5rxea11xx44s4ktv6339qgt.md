---
type: is
id: is-01m5rxea11xx44s4ktv6339qgt
title: "PR #59 Qodo 2: Python _required_layers accepts a mapping as require"
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
created_at: 2026-10-25T06:54:48.353Z
updated_at: 2026-10-25T07:16:48.123Z
started_at: 2026-10-25T06:54:53.994Z
closed_at: 2026-10-25T07:16:48.123Z
close_reason: "fixed in e02b064: _required_layers rejects Mapping with the same TypeError; test extended"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/59#discussion_r4369879126. validate.py:122-143. Fix: reject Mapping like str; test.
