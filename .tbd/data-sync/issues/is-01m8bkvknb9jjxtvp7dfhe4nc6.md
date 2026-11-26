---
type: is
id: is-01m8bkvknb9jjxtvp7dfhe4nc6
title: Add a bounded read-only collection API and scan command
kind: feature
status: in_progress
priority: 2
version: 4
delegate: codex@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-11-26T09:44:16.298Z
updated_at: 2026-11-26T18:39:31.135Z
started_at: 2026-11-26T09:45:22.605Z
---
Support the Metabrowser SoftSchema collection-table effort with portable scanning, schema binding, document outcomes, and refresh. Keep the Python and TypeScript CLI and public result semantics aligned.

## Notes

Implemented and independently rechecked the dual-runtime collection API in PR #78 at 7c13c9655. Corrected fallback under incomplete discovery, deletion tracking across bounded scans, and exact Markdown body preservation. Package release still pending.
