---
type: is
id: is-01m0qvyfjer4zak1yxgynnfd46
title: "PR42: Define declaration semantics for patternProperties"
kind: bug
status: open
priority: 2
version: 3
spec_path: docs/project/reviews/review-2026-08-23-pr-42-schema-composition-design.md
labels:
  - pr-42
  - json-schema
  - enforcement
dependencies: []
parent_id: is-01m0qtv9aebdaw48z0f70bjf87
created_at: 2026-08-23T17:50:57.612Z
updated_at: 2026-08-23T18:08:22.764Z
---
The declaration scan recognizes properties but not patternProperties. Pattern-only object schemas remain open, while a patternProperties sibling beside a ref can be rejected by lexical closure in the target.

## Notes

Published as a separately tracked finding in https://github.com/jlevy/softschema/pull/42#issuecomment-5387633246. Durable rationale and reproductions are in docs/project/reviews/review-2026-08-23-pr-42-schema-composition-design.md at commit 0efa042.
