---
type: is
id: is-01kt5qsvapxg72ammy9d1mksfg
title: Add publint as a dev dep + CI/release gate before npm publish
kind: task
status: closed
priority: 3
version: 3
spec_path: docs/project/specs/active/plan-2026-06-01-softschema-typescript-zod-parity.md
labels:
  - typescript
dependencies: []
created_at: 2026-06-03T03:18:00.785Z
updated_at: 2026-06-11T07:23:03.934Z
closed_at: 2026-06-11T07:23:03.934Z
close_reason: null
---
Senior review suggestion (PR #3). The npm package ships exports/bin/shebang/bundled resources/provenance; publint is a cheap publishability guard and was already named in the plan. Add publint as a devDependency in packages/typescript and run 'publint' in CI and before the npm publish step. Pin a reviewed version per the supply-chain cool-off.
