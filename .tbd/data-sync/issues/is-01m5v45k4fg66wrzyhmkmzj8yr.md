---
type: is
id: is-01m5v45k4fg66wrzyhmkmzj8yr
title: Name a near-miss undeclared key when a required property is missing (repair plan phase 4)
kind: feature
status: open
priority: 3
version: 1
labels: []
dependencies: []
created_at: 2026-10-26T03:30:51.663Z
updated_at: 2026-10-26T03:30:51.663Z
---
Phase 4 of docs/project/specs/done/plan-2026-08-29-validate-repair.md, deferred when phases 1-3 shipped in v0.8.0 and not started. Neither runtime implements it as of v0.9.0. `packages/typescript/src/repairConform.test.ts:249` pins the related rule that repair never renames a near-miss key; this feature reports one and does not rewrite it.

Scope:

- When a required property is missing and the instance has an undeclared near-miss key (for example `reason` where the contract wants `rationale`), name that key in the diagnostic.
- Extend the search to the frontmatter root, so a field mis-indented out of its envelope also gets a diagnostic.
- Emit byte-identical strings in both implementations, with golden coverage on Python, Node, and Bun.

Decide first (the plan's Open Question 4): put the hint in `message`, or in a new record field. Under the parity contract, any `message` wording change has to land in both implementations with golden updates. A separate field is cheaper to evolve and easier to match on. Either way the record surface changes, so the change lands on its own and needs a CHANGELOG entry.
