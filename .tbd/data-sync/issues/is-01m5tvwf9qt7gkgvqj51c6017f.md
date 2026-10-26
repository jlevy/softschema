---
type: is
id: is-01m5tvwf9qt7gkgvqj51c6017f
title: "Review G2: TS checkFlowMappingKey re-parses the document per explicit ? # comment key (quadratic)"
kind: bug
status: closed
priority: 1
version: 2
labels:
  - pr-64
  - review-G
dependencies: []
created_at: 2026-10-26T01:06:04.215Z
updated_at: 2026-10-26T01:10:08.305Z
closed_at: 2026-10-26T01:10:08.305Z
close_reason: "Fixed: explicitKeyIndex makes one lazy CST parse per document. 55 KB 0.33 s (123 s at ef45250), 112 KB 0.41 s; lib-units growth test 500 -> 5,000 keys. PR #64 head bac4d83 (fix 6dd53a6), CI run 40252506999 19/19; dispositions https://github.com/jlevy/softschema/pull/64#issuecomment-6405989887"
resolution: null
duplicate_of: null
---
isExplicitKey ran new Parser().parse(text) per key; 55 KB took 123 s. Fix: one lazy CST parse per document.
