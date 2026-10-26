---
type: is
id: is-01m5tvwhkjqkaegbs8bs3wcrq1
title: "Review G7: space-only line wider than an explicit block scalar indentation reads differently (silent)"
kind: bug
status: closed
priority: 2
version: 2
labels:
  - pr-64
  - review-G
dependencies: []
created_at: 2026-10-26T01:06:06.578Z
updated_at: 2026-10-26T01:10:10.134Z
closed_at: 2026-10-26T01:10:10.134Z
close_reason: "Fixed: both runtimes refuse a space-only line wider than parent column + explicit indicator. 3 vectors; spec and CHANGELOG. 160k fuzz: 0 silent. PR #64 head bac4d83 (fix 6dd53a6), CI run 40252506999 19/19; dispositions https://github.com/jlevy/softschema/pull/64#issuecomment-6405989887"
resolution: null
duplicate_of: null
---
key: >1 over four spaces is three spaces + newline in Python and empty in TS; 252 fuzz cases. Refuse in both.
