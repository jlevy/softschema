---
type: is
id: is-01m0qvy9wtr2s4sfejhcwnhsxs
title: "PR42: Alternatives closure changes anyOf and oneOf meaning"
kind: bug
status: open
priority: 1
version: 3
spec_path: docs/project/reviews/review-2026-08-23-pr-42-schema-composition-design.md
labels:
  - pr-42
  - json-schema
  - enforcement
dependencies: []
parent_id: is-01m0qtv9aebdaw48z0f70bjf87
created_at: 2026-08-23T17:50:51.801Z
updated_at: 2026-08-23T18:08:20.954Z
---
The enforced overlay closes anyOf/oneOf branches independently. It turns a raw-valid anyOf object invalid and can turn a raw-invalid oneOf object valid, contradicting the semantics-preservation invariant and Draft 2020-12 annotation behavior.

## Notes

Published as a separately tracked finding in https://github.com/jlevy/softschema/pull/42#issuecomment-5387633246. Durable rationale and reproductions are in docs/project/reviews/review-2026-08-23-pr-42-schema-composition-design.md at commit 0efa042.
