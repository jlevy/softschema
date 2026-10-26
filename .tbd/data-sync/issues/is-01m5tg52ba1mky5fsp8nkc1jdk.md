---
type: is
id: is-01m5tg52ba1mky5fsp8nkc1jdk
title: "PR #64 F3: integer -0 valid in Python but number_negative_zero in TS; flow-mapping key over 1,024 chars rejected by Python only"
kind: bug
status: closed
priority: 2
version: 2
labels:
  - pr-64
dependencies: []
created_at: 2026-10-25T21:41:02.954Z
updated_at: 2026-10-25T21:43:23.211Z
closed_at: 2026-10-25T21:43:23.211Z
close_reason: "Fixed in 62e88c3 (PR #64, head 6c366f6): Python rejects integer -0/-00 (and JSON -0) as number_negative_zero per the spec (constructor marks it, _check_value rejects; JSON path defers to ruamel); TS rejects an implicit flow-mapping key whose ':' is >1,024 code points after the key start or on a later line (ruamel's simple-key rule). Vectors negative_zero_integer(_padded), json_negative_zero_integer, positive_zero_integer, quoted_negative_zero, flow_mapping_key_at_limit/over_limit/astral_at_limit, json_key_over_limit, flow_mapping_key_colon_on_next_line, json_key_colon_on_next_line, flow_mapping_multiline_key. Residual (astral block keys, UTF-16 count in yaml) documented in spec/CHANGELOG, bead ss-irp6. CI run 40236576983: 19/19 pass. Dispositions: https://github.com/jlevy/softschema/pull/64#issuecomment-6403718248"
resolution: null
duplicate_of: null
---
Review F F3, Low, pre-existing. n: -0 / {"n": -0} read as 0 in Python, rejected in TS; {"<1,100-char key>": 1} a ruamel error, valid in TS. Same mechanism: a flow-mapping key whose ':' is on a later line ({"a"\n: 1}) is also Python-only rejected.
