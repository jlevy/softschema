---
type: is
id: is-01m5rztcfbk6pmj03h7yp9a5ce
title: "PR #59 D3: TS checks --require after --model import and file read"
kind: bug
status: closed
priority: 3
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rztad5krc4zxt6mw8qwhw7
hold: null
hold_until: null
created_at: 2026-10-25T07:36:21.227Z
updated_at: 2026-10-25T07:46:07.716Z
started_at: 2026-10-25T07:36:26.278Z
closed_at: 2026-10-25T07:46:07.716Z
close_reason: "fixed in 608bcc4: requiredChecksFromOpts called first in runValidate; golden case for unknown layer on a missing file"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5642075680. cli.ts runValidate. Fix: call requiredChecksFromOpts at the top.
