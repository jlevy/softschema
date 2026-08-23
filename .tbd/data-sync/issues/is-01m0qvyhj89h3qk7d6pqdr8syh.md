---
type: is
id: is-01m0qvyhj89h3qk7d6pqdr8syh
title: "PR42: Reconcile the enforced-closure documentation and issue links"
kind: task
status: open
priority: 1
version: 3
spec_path: docs/project/reviews/review-2026-08-23-pr-42-schema-composition-design.md
labels:
  - pr-42
  - documentation
  - design
dependencies: []
parent_id: is-01m0qtv9aebdaw48z0f70bjf87
created_at: 2026-08-23T17:50:59.655Z
updated_at: 2026-08-23T18:08:24.387Z
---
Make the spec, guide, Python/TypeScript design docs, code docstrings, vectors, and tracker describe one support profile. Current contradictions include the preservation invariant versus admitted residuals, a non-working nested-ref workaround, parity overclaims, stale error shapes, and the missing ss-p32o issue.

## Notes

Published as a separately tracked finding in https://github.com/jlevy/softschema/pull/42#issuecomment-5387633246. Durable rationale and reproductions are in docs/project/reviews/review-2026-08-23-pr-42-schema-composition-design.md at commit 0efa042.
