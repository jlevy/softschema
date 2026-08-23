---
type: is
id: is-01m0pjkm7kd2kf57ennae999ye
title: Document the closure rule, code enum, deviation policy, and upgrade path
kind: task
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-08-23-enforced-composition-closure.md
labels:
  - docs
dependencies: []
parent_id: is-01m0pjfmt8vxpkcjk8msfa8c32
created_at: 2026-08-23T05:48:30.322Z
updated_at: 2026-08-23T05:48:30.322Z
---
Phase 4.

- docs/softschema-spec.md Status Values: closure is no longer a single-keyword rule. State the applicator split, both keywords, and that fragments are never closed. Also document the annotation-aware widening: a property named in an if matcher is evaluated when the matcher succeeds and is therefore admitted (correct 2020-12 behavior, narrow, but should be documented rather than discovered).
- docs/softschema-spec.md error records: add the code table as the documented match surface; state which fields are stable across a minor and which are diagnostic.
- docs/softschema-guide.md line ~262: extend the Step 5 parenthetical so it stays true for composed schemas. Add a short cross-field rules example (decision: abandoned requires budget_spent) — its absence is part of why this limitation went unnoticed.
- docs/development.md: record the deviation policy — cross-implementation output is identical except for deviations explicitly checked in as documented diffs, Python goldens as reference.
- CHANGELOG: lead with the validator->code migration table under a 'breaking for consumers matching validator' heading. A stale validator == 'additionalProperties' check does not crash; it silently stops matching composed schemas — the one failure this change cannot make loud from inside the library.
