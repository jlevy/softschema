---
type: is
id: is-01kz5wzn3hs7e8ppgbt1nnzrnw
title: "PR #26: weak assertion reads.count(schema) <= 1 should be == 1"
kind: chore
status: closed
priority: 3
version: 2
labels: []
dependencies: []
parent_id: is-01kz5wzknpm4nrrjjjramv3x5d
created_at: 2026-08-04T08:07:03.025Z
updated_at: 2026-08-04T08:11:19.391Z
closed_at: 2026-08-04T08:11:19.391Z
close_reason: Now == 1, and counts YAML parses rather than file reads.
---
packages/python/tests/test_core.py: <= also passes on zero reads, which would mean something is badly wrong. (PR #26)
