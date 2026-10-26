---
type: is
id: is-01m5t0x050wdqtfm3rn9p0ytjc
title: "PR #62 E7: fuzz summary reads 'C parser on' when SOFTSCHEMA_PURE_YAML is set"
kind: task
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t0wx1zedsf15d8pn6cwkqx
created_at: 2026-10-25T17:14:29.920Z
updated_at: 2026-10-25T17:23:40.724Z
closed_at: 2026-10-25T17:23:40.724Z
close_reason: "fixed in 9f6cb2b: fuzz summary prints 'C parser gate on|off'; docstring says SOFTSCHEMA_PURE_YAML does not change the search"
resolution: null
duplicate_of: null
---
Low suggestion. devtools/yaml_parser_fuzz.py:368-372. Print 'C parser gate on/off' and say in the docstring the switch does not affect the search. https://github.com/jlevy/softschema/pull/62#pullrequestreview-5644280692
