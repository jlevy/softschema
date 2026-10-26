---
type: is
id: is-01m5tvwjzemwvyjy4t8qnbg24x
title: "Review G10: repair could quote number forms such as 1_000"
kind: task
status: closed
priority: 4
version: 2
labels:
  - pr-64
  - review-G
dependencies: []
created_at: 2026-10-26T01:06:07.982Z
updated_at: 2026-10-26T01:10:11.300Z
closed_at: 2026-10-26T01:10:11.299Z
close_reason: "Declined: repair must not change a value's type intent; quoting 1_000 picks one of the two readings the rule refuses. Rebuttal in https://github.com/jlevy/softschema/pull/64#issuecomment-6405989887"
resolution: canceled
duplicate_of: null
---
Suggestion to make repair quote a plain scalar that trips the number-form rule.
