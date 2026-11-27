---
type: is
id: is-01m8bkvknb9jjxtvp7dfhe4nc6
title: Add a bounded read-only collection API and scan command
kind: feature
status: in_progress
priority: 2
version: 9
delegate: codex@spud10.local
labels: []
dependencies: []
child_order_hints:
  - is-01m8cmv706qkqr4n2mhhnbhw3x
  - is-01m8cn371smmc04w3rptr8rpfs
  - is-01m8e674e5b6sp940m1gvy41kp
hold: null
hold_until: null
created_at: 2026-11-26T09:44:16.298Z
updated_at: 2026-11-27T09:53:32.455Z
started_at: 2026-11-26T09:45:22.605Z
---
Support the Metabrowser SoftSchema collection-table effort with portable scanning, schema binding, document outcomes, and refresh. Keep the Python and TypeScript CLI and public result semantics aligned.

## Notes

Merge-ready upstream stack #80: API #78 https://github.com/jlevy/softschema/pull/78 at e6ee08f330faed45bf4fd0b49709a5dfd28a9e12, release prep #79 https://github.com/jlevy/softschema/pull/79 at 625f299714ff63f66c703d80b93060d3a6981105. Both non-draft, MERGEABLE/CLEAN, all 19 CI checks green, no unresolved threads, no required approving reviews. Final independent follow-up D, security E, and performance F on #78 have no findings; #79 senior release/whole-stack review A has no findings. All per-PR and whole-stack guided-review references verified ready in Metabrowser. Merge, tag, and publication remain pending authorization. Optional streaming work stays ss-p0wt. Local parser timing sensitivity tracked separately in ss-3vkf.
