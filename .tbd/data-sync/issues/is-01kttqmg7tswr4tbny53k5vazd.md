---
type: is
id: is-01kttqmg7tswr4tbny53k5vazd
title: "[deferred] Trim/sanitize bundled agents+publishing docs topics; single shared resource manifest"
kind: task
status: closed
priority: 3
version: 3
labels: []
dependencies: []
created_at: 2026-06-11T06:59:08.666Z
updated_at: 2026-06-11T07:23:03.280Z
closed_at: 2026-06-11T07:23:03.280Z
close_reason: null
---
Deferred from Phase 4 (ss-3m4s landed the force-include drift guard instead). Two related items: (1) drop or sanitize the maintainer-facing 'agents' and 'publishing' docs topics (strip the tbd integration block from bundled AGENTS.md copies) — changes the public docs surface and golden docs --list output, so it is a product decision; (2) one shared manifest consumed by the wheel force-include, copy-resources.ts, and DOC_TOPICS, replacing three hand-maintained lists.
