---
type: is
id: is-01m5rxgenrg55fj5wx1wns83dx
title: "PR #64 A5: Python parse_frontmatter_text splits on splitlines(), TypeScript on \\r?\\n; U+2028/U+0085 diverge"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rxgc8kdy9fz5wgg3ew5vsq
hold: null
hold_until: null
created_at: 2026-10-25T06:55:58.647Z
updated_at: 2026-10-25T07:12:35.376Z
started_at: 2026-10-25T06:59:24.412Z
closed_at: 2026-10-25T07:12:35.376Z
close_reason: "fixed in 414a10f: parse_frontmatter_text splits on \\n and strips trailing \\r; shared vectors unicode_line_separators_in_scalar, unicode_line_separators_in_quoted_scalar, next_line_in_scalar fail before and pass after. Engine-level NEL/control-char divergence tracked as ss-6o9r."
resolution: null
duplicate_of: null
---
Medium, pre-existing. packages/python/src/softschema/validate.py:1068 vs packages/typescript/src/validate.ts:161. Split on \n and strip trailing \r; shared vector.
PR #64. Review A: https://github.com/jlevy/softschema/pull/64#pullrequestreview-5641911619
