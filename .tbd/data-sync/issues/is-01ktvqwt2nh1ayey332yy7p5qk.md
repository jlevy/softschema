---
type: is
id: is-01ktvqwt2nh1ayey332yy7p5qk
title: "P2: TS frontmatter: reject non-mapping frontmatter (frontmatter-format authority; closes ss-eero)"
kind: task
status: closed
priority: 1
version: 6
spec_path: docs/project/specs/done/plan-2026-06-11-softschema-terminology-and-linkage.md
labels: []
dependencies:
  - type: blocks
    target: is-01ktvqwtf685q8561mhxg2c15b
parent_id: is-01ktvqwp37dhdpgtqm6t9j6dkx
created_at: 2026-06-11T16:22:55.317Z
updated_at: 2026-07-10T03:49:22.064Z
---
Design 8: frontmatter-format's rules are authoritative for the frontmatter-md profile; TS readFrontmatter must reject a non-mapping parse like fmf_read does. Golden scenario; reconcile the CLI inferEnvelope path that currently emits 'candidates: 0, 1' nonsense.
