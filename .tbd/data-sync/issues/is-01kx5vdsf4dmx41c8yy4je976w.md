---
type: is
id: is-01kx5vdsf4dmx41c8yy4je976w
title: Normalize YAML composer errors before filesystem classification
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - parity
  - yaml
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx4scemwng8g758svkrcdnh9
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T11:08:25.444Z
updated_at: 2026-07-10T11:51:33.108Z
closed_at: 2026-07-10T11:51:33.107Z
close_reason: Normalized coded YAML parser/composer failures and restricted Node filesystem classification; paired parser and CLI regressions pass.
---
TypeScript YAML composer exceptions with a code field can be misclassified as filesystem input errors. Translate parser exceptions to PortableYamlSyntaxError with exact offsets and restrict filesystem classification to actual Node errors; add shared malformed-YAML CLI parity coverage.
