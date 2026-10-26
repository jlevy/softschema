---
type: is
id: is-01m5tvwj207s33nsz364nmzkbs
title: "Review G8: yaml package drops text on three malformed mapping-entry shapes Python refuses"
kind: bug
status: closed
priority: 2
version: 2
labels:
  - pr-64
  - review-G
dependencies: []
created_at: 2026-10-26T01:06:07.040Z
updated_at: 2026-10-26T01:10:10.481Z
closed_at: 2026-10-26T01:10:10.481Z
close_reason: "Fixed: TS checkDroppedContent refuses a mapping entry with a value, tag or anchor and no ':'. 3 vectors; spec and CHANGELOG. PR #64 head bac4d83 (fix 6dd53a6), CI run 40252506999 19/19; dispositions https://github.com/jlevy/softschema/pull/64#issuecomment-6405989887"
resolution: null
duplicate_of: null
---
a:\n- ? k\n  - x, {"a" : b , ""!}, - {k : v, ': '&'}: TS composes them with content missing. Refuse in TS.
