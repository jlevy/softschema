---
type: is
id: is-01m8bkvknb9jjxtvp7dfhe4nc6
title: Add a bounded read-only collection API and scan command
kind: feature
status: in_progress
priority: 2
version: 7
delegate: codex@spud10.local
labels: []
dependencies: []
child_order_hints:
  - is-01m8cmv706qkqr4n2mhhnbhw3x
  - is-01m8cn371smmc04w3rptr8rpfs
hold: null
hold_until: null
created_at: 2026-11-26T09:44:16.298Z
updated_at: 2026-11-26T19:29:49.873Z
started_at: 2026-11-26T09:45:22.605Z
---
Support the Metabrowser SoftSchema collection-table effort with portable scanning, schema binding, document outcomes, and refresh. Keep the Python and TypeScript CLI and public result semantics aligned.

## Notes

SoftSchema PR #78 e6ee08f implements the bounded eager collection API. Two parallel Astra reviews, 12 follow-up fixes and dispositions, and all 19 GitHub checks are complete. The package release is pending. The optional reference-first APIs are tracked separately under ss-p0wt.
