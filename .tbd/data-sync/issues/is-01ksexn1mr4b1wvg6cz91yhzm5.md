---
type: is
id: is-01ksexn1mr4b1wvg6cz91yhzm5
title: "[P0] SchemaView shared schema reader"
kind: feature
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/done/plan-2026-05-24-softschema-public-readiness.md
labels: []
dependencies:
  - type: blocks
    target: is-01ksexndke7ysd53r3jy3e0aq0
parent_id: is-01ksdw07thta724tst7r7nv1bp
created_at: 2026-05-25T06:37:42.935Z
updated_at: 2026-07-10T03:49:02.968Z
closed_at: 2026-05-26T07:40:52.585Z
close_reason: completed
---
Add softschema.schema_view.SchemaView wrapping a JSON Schema dict with stable methods for enums, required fields, field metadata, and x-softschema annotations. Single navigation API consumed by QA rules, agent prompts, comparison tooling, and generated sections. See plan Phase 5.
