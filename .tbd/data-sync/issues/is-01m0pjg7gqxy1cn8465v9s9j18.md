---
type: is
id: is-01m0pjg7gqxy1cn8465v9s9j18
title: "Python: replace enforcement refusal with applicator-split closure"
kind: bug
status: open
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-08-23-enforced-composition-closure.md
labels:
  - enforcement
dependencies:
  - type: blocks
    target: is-01m0pjkkgq8r3k9pe3eby7mz3b
  - type: blocks
    target: is-01m0pjkm7kd2kf57ennae999ye
parent_id: is-01m0pjfmt8vxpkcjk8msfa8c32
created_at: 2026-08-23T05:46:38.999Z
updated_at: 2026-08-23T05:48:30.322Z
---
Phase 2. Rewrite _apply_enforced_extras in packages/python/src/softschema/canonicalize.py to the three clauses in the spec:

1. Never inject closure inside a fragment subtree (thread an in_fragment flag; reset it under $defs, since definitions are complete declarations reached by $ref).
2. A node is property-declaring if it declares properties OR a fragment applicator under it declares properties (without this the composed_object vector is enforced nowhere).
3. Close such a node with unevaluatedProperties: false when it carries a fragment applicator, else additionalProperties: false. Explicit values still win; free-form mappings untouched.

Delete _contains_open_properties and EnforcementUnsupportedError (unreachable; no official surface — absent from __all__, index.ts, and every user-facing doc). Rewrite the two refusal-pinning tests as support assertions.
