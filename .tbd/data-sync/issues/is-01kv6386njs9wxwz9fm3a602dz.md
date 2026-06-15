---
type: is
id: is-01kv6386njs9wxwz9fm3a602dz
title: "errors.py/cli.py: _USER_ERRORS catches broad TypeError/ValueError/KeyError, can mask internal bugs"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
created_at: 2026-06-15T16:53:47.314Z
updated_at: 2026-06-15T17:41:50.750Z
closed_at: 2026-06-15T17:41:50.750Z
close_reason: Dropped TypeError/KeyError from the CLI user-error boundary so internal bugs surface; added UsageError + documented exit codes. Golden/cross-impl parity preserved.
---
