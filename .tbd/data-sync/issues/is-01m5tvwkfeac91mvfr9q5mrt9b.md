---
type: is
id: is-01m5tvwkfeac91mvfr9q5mrt9b
title: "TS: depth limit checked before the duplicate walk, counting empty collections as Python does"
kind: bug
status: closed
priority: 2
version: 2
labels:
  - pr-64
  - review-G
dependencies: []
created_at: 2026-10-26T01:06:08.494Z
updated_at: 2026-10-26T01:10:11.677Z
closed_at: 2026-10-26T01:10:11.677Z
close_reason: "Fixed: firstTooDeep checks the 64-collection limit first, iteratively, counting as Python; duplicate walk iterative and bounded. hostile_depth 0.40 s under Bun (13.5 s before). 3 vectors; CHANGELOG Depth limit; spec. PR #64 head bac4d83 (fix 6dd53a6), CI run 40252506999 19/19; dispositions https://github.com/jlevy/softschema/pull/64#issuecomment-6405989887"
resolution: null
duplicate_of: null
---
With uniqueKeys: false the duplicate walk ran before the depth refusal; Bun took 13.5 s on hostile_depth (0.3 s before). Also TS accepted an empty [] as the 65th open collection and reported yaml_duplicate_key for a too-deep document with an earlier duplicate, where Python says yaml_limit.
