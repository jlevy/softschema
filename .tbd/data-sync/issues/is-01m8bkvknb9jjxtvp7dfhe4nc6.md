---
type: is
id: is-01m8bkvknb9jjxtvp7dfhe4nc6
title: Add a bounded read-only collection API and scan command
kind: feature
status: in_progress
priority: 2
version: 3
delegate: codex@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-11-26T09:44:16.298Z
updated_at: 2026-11-26T10:41:20.494Z
started_at: 2026-11-26T09:45:22.605Z
---
Support the Metabrowser SoftSchema collection-table effort with portable scanning, schema binding, document outcomes, and refresh. Keep the Python and TypeScript CLI and public result semantics aligned.

## Notes

Implemented the Python and TypeScript collection API and scan CLI. All checks passed for https://github.com/jlevy/softschema/pull/78 at 611d0ec, including cross-implementation parity, Python 3.11–3.14 and release candidate smoke on macOS, Linux, and Windows. API package release remains pending.
