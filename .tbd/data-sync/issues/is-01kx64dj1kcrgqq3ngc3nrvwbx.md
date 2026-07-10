---
type: is
id: is-01kx64dj1kcrgqq3ngc3nrvwbx
title: Enforce TypeScript YAML node budgets during token iteration
kind: bug
status: closed
priority: 2
version: 9
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - typescript
  - yaml
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T13:45:35.026Z
updated_at: 2026-07-10T18:36:56.826Z
closed_at: 2026-07-10T18:36:56.825Z
close_reason: Implemented incremental TypeScript YAML construction budgets with parity coverage.
---
TypeScript spreads the full YAML CST token iterator before applying the 100,000-node budget, allowing under-byte-limit inputs to allocate well beyond policy. Count and abort while iterating tokens without weakening syntax diagnostics or source mapping.

## Notes

Reopened adversarial closure covers ordinary flow-scalar and empty-document floods, implicit-flow map node/depth accounting, exact first-limit paths, O(n) active flow checks, bounded discard after construction limit, and global syntax/semantic precedence including duplicate, merge, tag, alias, compact-flow, and depth combinations.
