---
type: is
id: is-01m5rsgkf3k91radfye0n9cm4r
title: "PR #59 A4: repair --check called a gate but has no require"
kind: bug
status: closed
priority: 3
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rr5w4r03h667rqqwvz0a5s
hold: null
hold_until: null
created_at: 2026-10-25T05:46:09.251Z
updated_at: 2026-10-25T06:13:12.241Z
started_at: 2026-10-25T05:46:17.632Z
closed_at: 2026-10-25T06:13:12.241Z
close_reason: "fixed in 39eac06 (minimal doc option): spec Repair section and both repair docstrings say repair takes no require and a gate that needs completed checks follows repair --check with validate --require"
resolution: null
duplicate_of: null
---
Severity: Low (suggestion). PR #59. Review A: https://github.com/jlevy/softschema/pull/59#pullrequestreview-5641723707. Refs: packages/python/src/softschema/pipeline.py:48-55, packages/typescript/src/repairValidate.ts:70-74, docs/softschema-spec.md Repair section. Fix (pick one): thread require through repair, or add a sentence to the spec Repair section pointing gates to validate --require.
