---
type: is
id: is-01ktvqwsay626pt02sc1aq5b52
title: "P2: softschema.schema metadata binding (JSON-Schema-first linkage)"
kind: feature
status: open
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-06-11-softschema-terminology-and-linkage.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktvqwtf685q8561mhxg2c15b
parent_id: is-01ktvqwp37dhdpgtqm6t9j6dkx
created_at: 2026-06-11T16:22:54.557Z
updated_at: 2026-06-11T16:38:32.473Z
---
Design 5: optional, RECOMMENDED-NOT-REQUIRED 'schema' key in the metadata block. contract alone is fully conforming (apps may resolve schemas out of band); schema is a recommended pointer for self-validating artifacts. Reference CLIs resolve the value relative to the document, bounded to doc-dir + cwd, but the SPEC only requires that schema (when present) be a non-empty string -- relative-from-document is a convention, not a conformance rule. Precedence: --schema flag (optional override, unnecessary when metadata key present) > softschema.schema metadata > registry schema_path > metadata-only. Unknown-key set becomes contract/status/schema. Golden scenarios: (a) bound artifact validates with NO flags; (b) --schema overrides the metadata key on a given run. Spec Metadata + Compiled Schemas + support-matrix updates in the same change.
