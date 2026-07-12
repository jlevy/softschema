---
type: is
id: is-01kxa2kh2agkcq5pa8mbkhd98h
title: "R5: align non-mapping schema reason across runtimes"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kxa14h09j4qnzmmj02pv5jzt
created_at: 2026-07-12T02:30:51.210Z
updated_at: 2026-07-12T02:32:16.842Z
closed_at: 2026-07-12T02:32:16.841Z
close_reason: Fixed in 341d001; focused and full validation passed, review thread replied to and resolved.
---
PR #21 review: TypeScript reports schema_invalid.reason=compilation for a compiled schema whose root is not a mapping, while Python reports syntax. Align TypeScript with Python and add focused parity coverage.
