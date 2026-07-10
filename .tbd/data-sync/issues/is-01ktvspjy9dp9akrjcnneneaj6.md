---
type: is
id: is-01ktvspjy9dp9akrjcnneneaj6
title: "P2: Generated-marker attribute rename contract= -> schema="
kind: feature
status: closed
priority: 2
version: 5
spec_path: docs/project/specs/active/plan-2026-06-11-softschema-terminology-and-linkage.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktvqwtf685q8561mhxg2c15b
parent_id: is-01ktvqwp37dhdpgtqm6t9j6dkx
created_at: 2026-06-11T16:54:28.552Z
updated_at: 2026-06-11T17:40:10.811Z
---
Design 7 + review finding 2. The generated-section marker attribute that holds a SCHEMA FILE PATH is spelled contract= today (e.g. softschema:generated kind=enum_table contract=movie-page.schema.yaml), which collides with the new terminology (contract = logical payload ID; schema = file pointer). Hard-rename the attribute to schema= in both parsers/renderers (generate.py/generate.ts), the spec examples, the movie-page README marker, and goldens; reject an old contract=...path... marker with a clear rename hint. Golden-first; one golden per kind (enum_table/field_list/vocab) pinning the normative output. No dual-accept (clean 0.2.0 break).
