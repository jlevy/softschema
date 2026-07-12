---
type: is
id: is-01kxa21k5ce733wjajmfwdttbr
title: "PR #21 review R4: align malformed schema reason as syntax"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kxa14h09j4qnzmmj02pv5jzt
created_at: 2026-07-12T02:21:03.531Z
updated_at: 2026-07-12T02:22:38.645Z
closed_at: 2026-07-12T02:22:38.644Z
close_reason: Fixed by classifying TypeScript PortableInputError schema-file failures as syntax, matching Python; full matrix passes.
---
PR #21 follow-up Bugbot medium finding at Python validate.py:142-144 and TypeScript validate.ts:376-378: malformed compiled YAML must report schema_invalid.reason syntax in both runtimes.
