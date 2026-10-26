---
type: is
id: is-01m5rz9jnqc8rcxwzqxp395ysx
title: Consume frontmatter-format libyaml guard once jlevy/frontmatter-format#9 lands
kind: task
status: closed
priority: 3
version: 2
labels: []
dependencies: []
created_at: 2026-10-25T07:27:10.519Z
updated_at: 2026-10-26T03:33:06.680Z
closed_at: 2026-10-26T03:33:06.679Z
close_reason: "Resolved by #70 (test-only): softschema keeps its stricter guard (a superset tied to its event pass), and a drift test runs a 5,750-text corpus through frontmatter-format 0.5.0's own guard (needs_pure_parser) — every text it routes to pure is refused, routed to pure, or read identically C-first vs pure by softschema; weakening softschema's guard fails it. Importing the guard at runtime was rejected: it is not public API and is less strict."
resolution: null
duplicate_of: null
---
From review D on #62 (https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642060738): the clean end state is frontmatter-format exporting needs_pure_parser with fixed regexes, a version gate and cost tests; softschema imports it, keeps its preflight and _check_value, and adds a parity test that every ROUTED_TO_PURE text is routed by the imported guard. Blocked on frontmatter-format#9 and a dependency bump under the cool-off policy.
