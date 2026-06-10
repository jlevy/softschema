---
type: is
id: is-01ktsqsahexgekyfrn6afdgvey
title: "P1: TypeScript validate.ts hardening (schema sidecar via parseYaml + non-mapping reject; structured parse_error on missing file)"
kind: task
status: open
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-06-10-softschema-review-remediation.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktsqsctqjmexdppec8ddj8rj
parent_id: is-01ktsqq6tmxwsdzynnxad1wv50
created_at: 2026-06-10T21:42:32.237Z
updated_at: 2026-06-10T21:43:55.085Z
---
FILE SCOPE: packages/typescript/src/validate.ts.
- structuralForValues: read schema sidecar via parseYaml wrapper (not raw yamlParse); if the parsed sidecar root is not a mapping, return a clean structural error rather than passing a bad cast to ajv.compile (MEDIUM 1.3).
- validateArtifact: catch ENOENT/read errors so a missing/unreadable doc returns a structured parse_error result instead of throwing (parity with Python P1 lib bead).
PARITY PAIR with P1 python validate bead. Tests in validate-extra.test.ts/standalone. Refs review TS 1.3.
