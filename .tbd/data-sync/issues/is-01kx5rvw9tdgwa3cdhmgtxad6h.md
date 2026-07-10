---
type: is
id: is-01kx5rvw9tdgwa3cdhmgtxad6h
title: Validate field annotations at both authoring boundaries
kind: bug
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - conformance
  - parity
  - api
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T10:23:41.369Z
updated_at: 2026-07-10T11:51:32.360Z
closed_at: 2026-07-10T11:51:32.359Z
close_reason: Validated field annotations at both authoring boundaries; compiler-profile and cross-runtime tests pass.
---
Python SoftFieldMeta and TypeScript softField authoring currently accept values (empty group/instruction, fractional order, and runtime-invalid enum strings in JavaScript) that the settled x-softschema fieldAnnotation schema rejects. Add identical authoring-boundary validation and stable errors in both runtimes, preserve valid annotations, and prove every official compiler output validates the public compiled profile and vocabulary.
