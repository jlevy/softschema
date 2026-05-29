---
type: is
id: is-01kshb6k5nqgyvs71hh2e83dpp
title: Tighten docs/softschema-spec.md to normative-only content
kind: task
status: closed
priority: 2
version: 3
spec_path: docs/project/reviews/review-2026-05-26-softschema-docs-design.md
labels: []
dependencies:
  - type: blocks
    target: is-01kshb8ac11et3tw1cxxjg2dgf
parent_id: is-01kshb5636qx5g9ha5xaa6b5qb
created_at: 2026-05-26T05:12:58.291Z
updated_at: 2026-05-26T05:53:12.479Z
closed_at: 2026-05-26T05:53:12.478Z
close_reason: completed
---
Per review Finding 5. The spec already is concise but still carries teaching content that overlaps with the guide. Tighten to answer only these questions:

- What files and profiles are in scope?
- What is the frontmatter shape?
- Is softschema optional or required in each state?
- What metadata keys are recognized?
- What is a valid contract ID?
- How is the envelope selected?
- What are valid status values?
- What are schema sidecars vs data sidecars?
- What is the source-of-truth order?
- What must a validator reject?
- Which features are explicitly NOT part of v0.1?

Motivation, adoption strategy, and large examples should live in the guide. Keep the example reference (small) but cut explanatory paragraphs that duplicate the guide.

Optional: review's proposed spec section list at lines 267-284.
