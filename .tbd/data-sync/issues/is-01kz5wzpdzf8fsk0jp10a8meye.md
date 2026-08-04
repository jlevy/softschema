---
type: is
id: is-01kz5wzpdzf8fsk0jp10a8meye
title: parse_yaml parses each document twice
kind: feature
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-08-04T08:07:04.382Z
updated_at: 2026-08-04T08:07:04.382Z
---
Event-stream preflight then a second construction pass; roughly 12x more work than a single pass with a C loader. Raised as follow-up in PR #27.
