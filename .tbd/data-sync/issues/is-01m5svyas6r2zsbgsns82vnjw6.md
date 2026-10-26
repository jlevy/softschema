---
type: is
id: is-01m5svyas6r2zsbgsns82vnjw6
title: Consume frontmatter-format's C-first libyaml guard once jlevy/frontmatter-format#9 lands (D7/D8 alignment)
kind: task
status: closed
priority: 3
version: 2
labels: []
dependencies: []
created_at: 2026-10-25T15:47:50.694Z
updated_at: 2026-10-26T03:33:07.189Z
closed_at: 2026-10-26T03:33:07.189Z
close_reason: "Resolved by #70 (test-only): softschema keeps its stricter guard (a superset tied to its event pass), and a drift test runs a 5,750-text corpus through frontmatter-format 0.5.0's own guard (needs_pure_parser) — every text it routes to pure is refused, routed to pure, or read identically C-first vs pure by softschema; weakening softschema's guard fails it. Importing the guard at runtime was rejected: it is not public API and is less strict."
resolution: null
duplicate_of: null
---
From review D on softschema PR #62 (https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642060738): two hand-maintained lists of libyaml shapes will drift. End state: frontmatter-format exports needs_pure_parser (or the whole C-first reader) with the fixed regexes (D7), a ruamel/libyaml version gate (D8) and the cost tests; softschema imports it, keeps its own preflight and _check_value, and keeps a parity test that every text in ROUTED_TO_PURE is routed by the imported guard. Blocked on frontmatter-format#9 merging and a frontmatter-format release that the cool-off policy admits (softschema pins frontmatter-format>=0.4.0 under exclude-newer). Softschema beads ss-t28j (D7) and ss-tula (D8) record the findings as owned by frontmatter-format.
