---
type: is
id: is-01kyxb333jxgq86mecwed57z23
title: "PR #23 review I4: Clarify Pydantic and Zod date accept-set differences"
kind: bug
status: closed
priority: 2
version: 3
labels:
  - pr-23-review
dependencies: []
parent_id: is-01kyxb2jmbakcvq711fj9yfdde
created_at: 2026-08-01T00:20:25.842Z
updated_at: 2026-08-01T00:35:43.501Z
closed_at: 2026-08-01T00:35:43.501Z
close_reason: Fixed in 59d2289; full local validation and all 19 PR checks passed.
---
Review issue 4 across the guide and package design docs. Remove wording that implies Pydantic date/datetime and Zod ISO schemas have equivalent accept-sets. Explain that portable decoding accepts date-shaped strings independently, each semantic model defines its own accepted spellings, and cross-runtime hosts requiring identical semantics must author matching validators.
