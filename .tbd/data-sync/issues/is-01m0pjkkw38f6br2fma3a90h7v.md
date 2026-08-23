---
type: is
id: is-01m0pjkkw38f6br2fma3a90h7v
title: Pin known cross-implementation error deviations as documented diffs
kind: task
status: closed
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-08-23-enforced-composition-closure.md
labels:
  - testing
  - parity
dependencies: []
parent_id: is-01m0pjfmt8vxpkcjk8msfa8c32
created_at: 2026-08-23T05:48:29.955Z
updated_at: 2026-08-23T06:31:38.529Z
closed_at: 2026-08-23T06:31:38.528Z
close_reason: "Landed on claude/review-open-issue-spec-dt4zkk (PR #42)."
resolution: null
duplicate_of: null
---
Maintainer direction: functionally equivalent, language-native error differences are fine WHEN TESTS DOCUMENT THEM. Python goldens are the reference output; accepted TypeScript deviations are checked in and validated, so a known deviation passes while any UNLISTED divergence still fails.

Seed the deviation list with two entries:
1. dependentSchemas: when a dependent schema fails, ajv adds an unevaluatedProperties record naming a property that top-level properties already evaluated; Python reports only 'required'. Both agree the document is invalid.
2. anyOf (pre-existing, currently untested): Python emits one anyOf record; ajv emits two 'type' plus one anyOf. This ships today unpinned — this fix is the occasion to pin it.

Wire the mechanism through tests/golden/cross-impl-diff.sh.
