---
type: is
id: is-01kxa2yknyhtxdptfg1401t93q
title: "R6: normalize non-mapping frontmatter error text"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kxa14h09j4qnzmmj02pv5jzt
created_at: 2026-07-12T02:36:54.333Z
updated_at: 2026-07-12T02:38:39.102Z
closed_at: 2026-07-12T02:38:39.101Z
close_reason: Fixed in d7b4eec; exact message assertions and complete validation passed, review thread replied to and resolved.
---
PR #21 review: Python and TypeScript reject non-mapping frontmatter but serialize different type wording in yaml_parse_error. Choose one canonical message, align both runtimes, and add direct parity coverage.
