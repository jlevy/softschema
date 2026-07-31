---
type: is
id: is-01kyx93bh11rmrma1zvkh6m2gy
title: Run paired-runtime release validation
kind: task
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-07-31-portable-yaml-timestamps.md
labels:
  - github-22
  - validation
dependencies: []
parent_id: is-01kyx90yh6vv5n0jdmhh5dar9n
created_at: 2026-07-31T23:45:37.312Z
updated_at: 2026-07-31T23:45:37.312Z
---
Run the complete matrix required by docs/development.md: shared conformance, Python unit suite and static checks, TypeScript lint/typecheck/coverage suite, Python/Node/Bun goldens, cross-language compiled schema and digest parity, source-skill mirror drift, bundled-resource tests, documentation lint and footer checks, wheel/sdist/npm builds, publint, and clean-install smoke tests that import each public package and print the bundled updated spec. Review git diff --check and reconcile the plan plus every child bead. Acceptance: every command passes, the plan reports Implemented with no open decisions, and no untracked follow-up remains.
