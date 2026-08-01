---
type: is
id: is-01kyxb333jxgq86mecwed57z23
title: "PR #23 review I4: Clarify Pydantic and Zod date accept-set differences"
kind: bug
status: open
priority: 2
version: 1
labels:
  - pr-23-review
dependencies: []
parent_id: is-01kyxb2jmbakcvq711fj9yfdde
created_at: 2026-08-01T00:20:25.842Z
updated_at: 2026-08-01T00:20:25.842Z
---
Review issue 4 across the guide and package design docs. Remove wording that implies Pydantic date/datetime and Zod ISO schemas have equivalent accept-sets. Explain that portable decoding accepts date-shaped strings independently, each semantic model defines its own accepted spellings, and cross-runtime hosts requiring identical semantics must author matching validators.
