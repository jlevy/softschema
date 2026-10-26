---
type: is
id: is-01m5tg51xt93pgwmrz4rde320c
title: "PR #64 F2: yaml package rejects a flow continuation line in block context that ruamel reads (tab-indented quoted/flow continuation)"
kind: bug
status: closed
priority: 2
version: 2
labels:
  - pr-64
dependencies: []
created_at: 2026-10-25T21:41:02.521Z
updated_at: 2026-10-25T21:43:22.842Z
closed_at: 2026-10-25T21:43:22.842Z
close_reason: "Fixed in 62e88c3 (PR #64, head 6c366f6) by making both runtimes agree: Python's event pass (_FlowIndentation in _portable.py) rejects a later line of a flow collection or quoted scalar in block context not indented with spaces past its parent, mirroring the yaml lexer (blank lines, comment lines in flow, closing bracket at parent column, root flow/JSON exempt). Spec Portable YAML Values and CHANGELOG Compatibility document it; 12 portable_values vectors. 30,000-case generated sweep: 5 residual cases, all rejected by both (duplicate-key precedence); old reader mismatched 3,368/8,000 on one seed; C-first == pure on all; 2 MB parse time within noise. CI run 40236576983: 19/19 pass. Dispositions: https://github.com/jlevy/softschema/pull/64#issuecomment-6403718248"
resolution: null
duplicate_of: null
---
Review F F2, Low, pre-existing. title: "first\n<TAB>  second" and tags: [a,\n<TAB>b] read in Python, fail in node/bun. Root cause is broader than tabs: YAML 1.2 requires later lines of a flow collection or quoted scalar in block context to be indented with spaces past the parent block; yaml enforces it, ruamel does not (space-only under-indentation differs too).
