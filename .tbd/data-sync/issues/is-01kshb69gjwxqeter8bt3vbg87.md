---
type: is
id: is-01kshb69gjwxqeter8bt3vbg87
title: Confirm public API naming with trading consumer seam
kind: task
status: closed
priority: 2
version: 2
spec_path: docs/project/reviews/review-2026-05-26-softschema-docs-design.md
labels: []
dependencies: []
parent_id: is-01kshb5636qx5g9ha5xaa6b5qb
created_at: 2026-05-26T05:12:48.401Z
updated_at: 2026-05-26T05:53:13.029Z
closed_at: 2026-05-26T05:53:13.028Z
close_reason: completed
---
Before the trading repo cuts over, confirm public API names. The trading consumer plan (aisw/trading/docs/project/specs/active/plan-2026-05-24-softschema-open-source-adoption.md line 574) drafted the API as:

    from softschema import SchemaBinding, SchemaRegistry, Status, validate_artifact

The current package (packages/python/src/softschema/__init__.py) exports namespaced names:

    SoftschemaBinding, SoftschemaRegistry, SoftschemaStatus, SoftschemaMetadata,
    SoftschemaProfile, SoftschemaStage, SoftschemaWarning, validate_artifact, ...

The namespaced forms avoid collisions with generic 'Status'/'Binding' in consumer code. The trading-plan forms are shorter and read better in adoption examples. Pick one before public release — renaming after publishing is a breaking change.

This is a one-shot decision because the trading monorepo will write 'from softschema import ...' in many places during Phase 3 cutover; changing later forces a coordinated rename across both repos.
