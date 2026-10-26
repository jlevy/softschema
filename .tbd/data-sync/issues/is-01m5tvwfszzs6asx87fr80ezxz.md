---
type: is
id: is-01m5tvwfszzs6asx87fr80ezxz
title: "Review G3: block scalar at end of YAML text reads text in Python and text\\n in TS (frontmatter last key, pure-yaml without final newline)"
kind: bug
status: closed
priority: 1
version: 2
labels:
  - pr-64
  - review-G
dependencies: []
created_at: 2026-10-26T01:06:04.735Z
updated_at: 2026-10-26T01:10:08.707Z
closed_at: 2026-10-26T01:10:08.707Z
close_reason: "Fixed: parse_yaml/parsePortableYaml append the final line break; Python clip/keep at end of input now end with \\n (CHANGELOG names Python). 8 vectors (frontmatter + pure-yaml, | > |+ |-). Spec and CHANGELOG. PR #64 head bac4d83 (fix 6dd53a6), CI run 40252506999 19/19; dispositions https://github.com/jlevy/softschema/pull/64#issuecomment-6405989887"
resolution: null
duplicate_of: null
---
Both readers must hand the parser text ending in a line break; vectors for | > |+ |- in frontmatter and pure-yaml; CHANGELOG names Python as the runtime whose value changes.
