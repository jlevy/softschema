---
type: is
id: is-01ktvqwsay626pt02sc1aq5b52
title: "P2: softschema.schema metadata binding (JSON-Schema-first linkage)"
kind: feature
status: open
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-06-11-softschema-terminology-and-linkage.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktvqwtf685q8561mhxg2c15b
parent_id: is-01ktvqwp37dhdpgtqm6t9j6dkx
created_at: 2026-06-11T16:22:54.557Z
updated_at: 2026-06-11T16:22:57.907Z
---
Design 5: optional 'schema' key in the metadata block (relative path resolved from the document directory only); precedence --schema flag > metadata > registry schema_path > metadata-only; unknown-key set becomes contract/status/schema; golden scenario: bound artifact validates with NO flags. Spec Metadata + Compiled Schemas + support-matrix updates in the same change.
