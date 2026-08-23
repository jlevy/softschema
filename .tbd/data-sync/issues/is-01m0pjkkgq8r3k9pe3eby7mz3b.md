---
type: is
id: is-01m0pjkkgq8r3k9pe3eby7mz3b
title: "TypeScript: port closure rule, code enum, and ajv error normalization"
kind: bug
status: open
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-08-23-enforced-composition-closure.md
labels:
  - enforcement
  - parity
dependencies:
  - type: blocks
    target: is-01m0pjkkw38f6br2fma3a90h7v
  - type: blocks
    target: is-01m0pjkm7kd2kf57ennae999ye
parent_id: is-01m0pjfmt8vxpkcjk8msfa8c32
created_at: 2026-08-23T05:48:29.590Z
updated_at: 2026-08-23T05:48:30.322Z
---
Phase 3. Mirror the Python work in packages/typescript/src/.

- canonicalize.ts: same three-clause closure rule (applicator split, fragments never closed).
- errors.ts: matching message template, code enum, and keyword->code map.
- Generalize collapseAdditionalProperties to collapse on the undeclared_property code, renaming it for what it now does. Needed because ajv (allErrors) emits one closure error PER KEY while Python jsonschema emits one per object; softschema records carry no key names, so post-normalization records for one path are byte-identical and keeping the first reproduces Python's shape.
- Suppress ajv's 'if' wrapper records in normalizeAjvError's caller: for the issue #41 violating case ajv emits both 'required' and an 'if' wrapper ('must match "then" schema'), while Python emits only 'required'. A failing if is a false condition, not an error, so dropping the wrapper aligns to Python without losing information.
