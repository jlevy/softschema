---
type: is
id: is-01kshb5xk61cvpc18r7tk88n12
title: "Confirm v0.1 artifact shape: keep one-envelope, defer softschema.values pointer"
kind: task
status: closed
priority: 2
version: 2
spec_path: docs/project/reviews/review-2026-05-26-softschema-docs-design.md
labels: []
dependencies: []
parent_id: is-01kshb5636qx5g9ha5xaa6b5qb
created_at: 2026-05-26T05:12:36.197Z
updated_at: 2026-05-26T05:53:12.237Z
closed_at: 2026-05-26T05:53:12.235Z
close_reason: completed
---
Per review Finding 2 (current vs future state mixing). The guide and spec describe one top-level payload envelope beside softschema: (which matches the code, examples, and CLI inference). The to-be-removed design doc introduced softschema.values: {location, pointer} as the 'canonical shape for new documents'. That is a normative conflict — a reader can't tell which shape is valid today.

Recommendation: keep one-envelope-beside-softschema for v0.1 with envelope inference when exactly one non-softschema top-level key exists. Move softschema.values to the active plan as a deferred design option. Do not adopt softschema.values for v0.1 unless the implementation, examples, CLI, and tests all change together (partial adoption would make the format ambiguous — see review Residual Risks).
