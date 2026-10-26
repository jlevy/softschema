---
type: is
id: is-01m5tvwewbqanpzdzc4b9hwxzn
title: 'Review G1: Python reader quadratic on quoted scalars or flow collections with no # (per-event "#" in text)'
kind: bug
status: closed
priority: 1
version: 2
labels:
  - pr-64
  - review-G
dependencies: []
created_at: 2026-10-26T01:06:03.787Z
updated_at: 2026-10-26T01:10:07.906Z
closed_at: 2026-10-26T01:10:07.906Z
close_reason: "Fixed: has_hash computed once per document in _parse_with. Deterministic test counts whole-text substring tests: 9 at 10 and 1,000 lines (38 -> 3,008 at ef45250). Python 5 MB flow_lists 14.7 s (main 12.8 s, ef45250 73 s); every perf shape linear. PR #64 head bac4d83 (fix 6dd53a6), CI run 40252506999 19/19; dispositions https://github.com/jlevy/softschema/pull/64#issuecomment-6405989887"
resolution: null
duplicate_of: null
---
ef45250 da64537: `"#" in text` ran per quoted scalar event and per flow collection end; 5 MB flow_lists 73 s vs 13 s at main. Fix: hoist once per document; pin with a deterministic count.
