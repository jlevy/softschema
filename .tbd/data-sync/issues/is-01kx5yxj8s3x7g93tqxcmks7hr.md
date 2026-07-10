---
type: is
id: is-01kx5yxj8s3x7g93tqxcmks7hr
title: Separate registry README versions from source bootstrap pins
kind: bug
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - release
dependencies:
  - type: blocks
    target: is-01kx4w3nqewdhf1d3g0xgvj4ra
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:09:28.088Z
updated_at: 2026-07-10T12:50:40.384Z
closed_at: 2026-07-10T12:50:40.383Z
close_reason: PyPI now uses the package-specific Python README and both registry READMEs are version-bound, while root/source/skill docs remain verified-pin-bound; public claims and bootstrap tests pass.
---
PyPI and npm package pages must describe the candidate artifact version, while root quickstarts and agent discovery must remain on the last dual-registry-verified pin until publication succeeds. Use packages/python/README.md as PyPI metadata, keep the TypeScript package README version-bound, add authoritative public-claim markers, and test registry versions separately from source bootstrap pins.
