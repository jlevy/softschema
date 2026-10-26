---
type: is
id: is-01m5svyas6r2zsbgsns82vnjw6
title: Consume frontmatter-format's C-first libyaml guard once jlevy/frontmatter-format#9 lands (D7/D8 alignment)
kind: task
status: open
priority: 3
version: 1
labels: []
dependencies: []
created_at: 2026-10-25T15:47:50.694Z
updated_at: 2026-10-25T15:47:50.694Z
---
From review D on softschema PR #62 (https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642060738): two hand-maintained lists of libyaml shapes will drift. End state: frontmatter-format exports needs_pure_parser (or the whole C-first reader) with the fixed regexes (D7), a ruamel/libyaml version gate (D8) and the cost tests; softschema imports it, keeps its own preflight and _check_value, and keeps a parity test that every text in ROUTED_TO_PURE is routed by the imported guard. Blocked on frontmatter-format#9 merging and a frontmatter-format release that the cool-off policy admits (softschema pins frontmatter-format>=0.4.0 under exclude-newer). Softschema beads ss-t28j (D7) and ss-tula (D8) record the findings as owned by frontmatter-format.
