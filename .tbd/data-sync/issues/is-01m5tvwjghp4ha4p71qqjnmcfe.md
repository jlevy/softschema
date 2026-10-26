---
type: is
id: is-01m5tvwjghp4ha4p71qqjnmcfe
title: "Review G9: TS reader quadratic in mapping width (uniqueKeys: true)"
kind: bug
status: closed
priority: 2
version: 2
labels:
  - pr-64
  - review-G
dependencies: []
created_at: 2026-10-26T01:06:07.504Z
updated_at: 2026-10-26T01:10:10.847Z
closed_at: 2026-10-26T01:10:10.847Z
close_reason: "Fixed: uniqueKeys: false plus firstDuplicateKey (one pass, set per mapping, prettifyError-format message). 0.4 MB block_numbers 0.43 s (main 6.34 s), flow_map_many_keys 0.66 s (main 16.7 s). Message test vs the package on 8 documents; fuzz: 3,365/3,370 kinds and 3,330 messages identical. PR #64 head bac4d83 (fix 6dd53a6), CI run 40252506999 19/19; dispositions https://github.com/jlevy/softschema/pull/64#issuecomment-6405989887"
resolution: null
duplicate_of: null
---
uniqueKeys: false plus a linear duplicate check with the same kind, message and position.
