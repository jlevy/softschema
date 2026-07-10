---
type: is
id: is-01kx5p5ze8zyggxrrc4f2c8227
title: Anchor extra-property diagnostics to the offending key
kind: bug
status: closed
priority: 2
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - diagnostics
  - parity
dependencies:
  - type: blocks
    target: is-01kx4vfebyfym3whq7f3e3x0qs
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T09:36:46.535Z
updated_at: 2026-07-10T09:47:30.000Z
closed_at: 2026-07-10T09:47:29.999Z
close_reason: Implemented and verified across Python and TypeScript with shared multiple-extra and escaped-key location tests.
---
Batch diagnostic-v1 currently asks SourceMap for a key span at the containing object path for additionalProperties/unevaluatedProperties, so it anchors the envelope/object key rather than the actual disallowed property. Preserve an internal, non-wire diagnostic instance path from Python jsonschema and Ajv (without changing legacy single-file bytes), choose a stable offending key when an engine reports multiple extras, use its key span in diagnostic-v1, retain containing-object fallback when no structured key exists, and add shared Python/Node/Bun tests including escaped JSON Pointer keys.

## Notes

Implemented non-wire structured offending-property hints from jsonschema/Ajv, deterministic Unicode-min selection for multiple extras, escaped JSON Pointer paths, and key-span anchors for both additionalProperties and unevaluatedProperties with containing-object fallback. Shared Python/Bun CLI vectors pass; legacy structural keys and cross-implementation bytes are unchanged.
