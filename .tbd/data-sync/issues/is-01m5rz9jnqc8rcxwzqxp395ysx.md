---
type: is
id: is-01m5rz9jnqc8rcxwzqxp395ysx
title: Consume frontmatter-format libyaml guard once jlevy/frontmatter-format#9 lands
kind: task
status: open
priority: 3
version: 1
labels: []
dependencies: []
created_at: 2026-10-25T07:27:10.519Z
updated_at: 2026-10-25T07:27:10.519Z
---
From review D on #62 (https://github.com/jlevy/softschema/pull/62#pullrequestreview-5642060738): the clean end state is frontmatter-format exporting needs_pure_parser with fixed regexes, a version gate and cost tests; softschema imports it, keeps its preflight and _check_value, and adds a parity test that every ROUTED_TO_PURE text is routed by the imported guard. Blocked on frontmatter-format#9 and a dependency bump under the cool-off policy.
