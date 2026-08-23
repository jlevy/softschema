---
type: is
id: is-01m0pjfmt8vxpkcjk8msfa8c32
title: "Spec: enforced closure for composed schemas (issue #41)"
kind: epic
status: closed
priority: 1
version: 8
spec_path: docs/project/specs/active/plan-2026-08-23-enforced-composition-closure.md
labels:
  - enforcement
  - json-schema
  - parity
dependencies: []
child_order_hints:
  - is-01m0pjg74rvw119xd89239fg1q
  - is-01m0pjg7gqxy1cn8465v9s9j18
  - is-01m0pjg7wgjcrrempb9phraen0
  - is-01m0pjkkgq8r3k9pe3eby7mz3b
  - is-01m0pjkkw38f6br2fma3a90h7v
  - is-01m0pjkm7kd2kf57ennae999ye
created_at: 2026-08-23T05:46:19.848Z
updated_at: 2026-08-23T06:31:39.046Z
closed_at: 2026-08-23T06:31:39.046Z
close_reason: "All six children landed on PR #42. Issue #41 resolved: composed schemas validate under enforced, records carry a stable code enum, engine deviations pinned. Sibling anyOf bug filed as ss-p32o."
resolution: null
duplicate_of: null
---
Under `status: enforced`, any schema using `allOf`/`if`/`then` composition fails with `enforcement_unsupported` for every document, so a genuine violation is masked by a generic message (GitHub issue #41).

Root cause: `additionalProperties` is lexical and cannot see properties contributed by sibling subschemas, so the overlay refuses rather than closing. Fix: split applicators into alternatives (`anyOf`/`oneOf`, closed per branch as today) and fragments (`allOf`, `if`/`then`/`else`, `not`, `dependentSchemas`, never closed), and close composition roots with `unevaluatedProperties: false`.

Validated by prototype: reporter's cases resolve, 174/176 Python tests and all 44 golden scenarios pass; the 2 failures are exactly the tests pinning the old refusal.

Maintainer direction folded in: (1) structural error records gain a stable `code` enum so consumers match categories not engine keywords; (2) support `dependentSchemas`, accepting language-native error differences documented as checked-in diffs against the Python golden reference; (3) ship as a minor that may break a little, with a clear upgrade path and obvious failures.

Full design, evidence tables, and upgrade path: docs/project/specs/active/plan-2026-08-23-enforced-composition-closure.md
