---
type: is
id: is-01kshb7zwjhyehkvwq9x9v9gc3
title: Move docs/research/ under docs/project/research/
kind: task
status: closed
priority: 3
version: 3
spec_path: docs/project/reviews/review-2026-05-26-softschema-docs-design.md
labels: []
dependencies:
  - type: blocks
    target: is-01kshb8ac11et3tw1cxxjg2dgf
parent_id: is-01kshb5636qx5g9ha5xaa6b5qb
created_at: 2026-05-26T05:13:44.081Z
updated_at: 2026-05-26T05:53:11.010Z
closed_at: 2026-05-26T05:53:11.009Z
close_reason: completed
---
Per review Finding 7. Public docs should live at docs/ root; project-internal design history should live under docs/project/. Currently docs/research/ sits at the docs root, where readers may treat it as part of the public product documentation.

Action:
1. git mv docs/research docs/project/research
2. Fix the one reference in docs/softschema-design.md References section (if the file still exists after ss-wut9 lands) — or in the active plan that referenced research-2026-05-24-softschema-runtime-design-v8.md
3. Run rg 'docs/research/' . to catch other references

Optional per the review, but consistent with the public/private docs boundary the review proposes.
