---
type: is
id: is-01ktvqwryjajbrazxy7k4hzcn7
title: "P2: Enforce contract-ID grammar"
kind: feature
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/done/plan-2026-06-11-softschema-terminology-and-linkage.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktvqwtf685q8561mhxg2c15b
parent_id: is-01ktvqwp37dhdpgtqm6t9j6dkx
created_at: 2026-06-11T16:22:54.162Z
updated_at: 2026-07-10T03:49:21.493Z
---
Design 4 grammar ([namespace:]name[/version], segment rules, no whitespace, at most one ':' and '/'), validated in both implementations with clean exit-2 diagnostics; UpperCamelCase stays advisory. Golden-first shared scenarios; spec Contract IDs section updated in the same change.
