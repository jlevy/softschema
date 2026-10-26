---
type: is
id: is-01m5rztb3rzp3za88fpbphdkaw
title: "PR #59 D1: nullable and $recursiveRef honored by Ajv only, unpinned"
kind: bug
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/done/plan-2026-09-12-validation-execution-evidence.md
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rztad5krc4zxt6mw8qwhw7
hold: null
hold_until: null
created_at: 2026-10-25T07:36:19.832Z
updated_at: 2026-10-26T03:34:08.689Z
started_at: 2026-10-25T07:36:25.292Z
closed_at: 2026-10-25T07:46:06.751Z
close_reason: "fixed in 7aded61: nullable, $recursiveRef, $recursiveAnchor refused as dialect in both runtimes (_FOREIGN_KEYWORDS/FOREIGN_KEYWORDS); vectors nullable-keyword, property-named-nullable, recursive-ref-keyword, recursive-anchor-keyword; Compatibility note in 788c61b"
resolution: null
duplicate_of: null
---
Medium. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5642075680. validate.py _check_dialect, validate.ts checkDialect. Fix: refuse both as dialect in both runtimes; vectors; Compatibility note.
