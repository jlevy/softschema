---
type: is
id: is-01kyxb32sr4p4brpczdd8dzzx8
title: "PR #23 review I3: Document semantic strictness outside schema digests"
kind: bug
status: closed
priority: 2
version: 3
labels:
  - pr-23-review
dependencies: []
parent_id: is-01kyxb2jmbakcvq711fj9yfdde
created_at: 2026-08-01T00:20:25.527Z
updated_at: 2026-08-01T00:35:43.494Z
closed_at: 2026-08-01T00:35:43.494Z
close_reason: Fixed in 59d2289; full local validation and all 19 PR checks passed.
---
Review issue 3 at packages/typescript/src/compile.ts:130. State normatively that compiler normalization intentionally omits semantic-model refinements such as Zod datetime offset, local, and precision options from the structural sidecar and schema_sha256. Add a regression proving variants share the structural schema while semantic validation remains model-specific.
