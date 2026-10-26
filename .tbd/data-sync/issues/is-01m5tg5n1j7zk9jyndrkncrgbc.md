---
type: is
id: is-01m5tg5n1j7zk9jyndrkncrgbc
title: "Block-mapping and flow-sequence-pair key limit: TS counts 1,024 in UTF-16 units, Python in code points"
kind: bug
status: closed
priority: 3
version: 2
labels:
  - pr-64
dependencies: []
created_at: 2026-10-25T21:41:22.098Z
updated_at: 2026-10-25T23:11:08.921Z
closed_at: 2026-10-25T23:11:08.921Z
close_reason: "Fixed in 3bbcf3c (PR #64, head ef45250): Python measures the 1,024 implicit-key limit in UTF-16 code units for block-mapping keys and flow-sequence pairs, as the yaml package does; explicit pairs exempt (da64537). 48 astral cases agree in py C-first, pure and TS; vectors block_key_astral_at/over_utf16_limit, flow_pair_key_astral_at/over_utf16_limit, flow_pair_explicit_key_astral. Spec 'One difference remains' sentence replaced. CI run 40243372151 19/19. Addendum: https://github.com/jlevy/softschema/pull/64#issuecomment-6404713010"
resolution: null
duplicate_of: null
---
Found while fixing PR #64 review F3. The yaml package's KEY_OVER_1024_CHARS check (resolve-block-map.js, resolve-flow-collection.js) uses UTF-16 offsets; ruamel uses code points. A block key of 600 U+1F600 characters (1,200 UTF-16 units) is rejected by TS and read by Python; same for [<600 emoji>: 1]. Loud (exit 2 vs 0). Documented as a remaining difference in docs/softschema-spec.md (Portable YAML Values) and the CHANGELOG Compatibility note. Fix would be a Python check counting UTF-16 units for block-map keys and flow-seq pairs, or leave documented.
