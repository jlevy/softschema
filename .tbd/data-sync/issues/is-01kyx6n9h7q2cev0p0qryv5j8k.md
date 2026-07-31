---
type: is
id: is-01kyx6n9h7q2cev0p0qryv5j8k
title: Normalize YAML timestamps to portable strings
kind: feature
status: closed
priority: 2
version: 8
spec_path: docs/project/specs/active/plan-2026-07-31-portable-yaml-timestamps.md
labels:
  - github-22
dependencies: []
created_at: 2026-07-31T23:02:59.366Z
updated_at: 2026-07-31T23:43:04.659Z
closed_at: 2026-07-31T23:43:04.658Z
close_reason: "Issue #22 implementation, migration path, specification, design docs, agent guidance, parity fixtures, and full validation matrix are complete. Publishing remains a separate maintainer action."
---
Implement GitHub issue #22 according to the focused plan: decode implicit YAML timestamp scalars as portable strings in both runtimes, preserve parser isolation and scalar content, align host-native date guards, add parity and semantic tests, update every assigned documentation surface, regenerate skill mirrors, and prepare the paired minor release. https://github.com/jlevy/softschema/issues/22

## Notes

Decision-complete and implemented on codex/issue-22-analysis. Implicit YAML timestamps decode as portable strings; format is unconditionally annotation-only; semantic models own calendar validity; explicit assertions remain structural; Pydantic/Zod date schemas now compile canonically. Full Python, TypeScript, cross-runtime golden/conformance, build, documentation, mirror, and clean wheel/sdist/npm package-smoke validation passed.
