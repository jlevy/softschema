---
type: is
id: is-01kyxb32hstvhdan8d6zzwx32t
title: "PR #23 review I2: Normalize all portable Zod ISO string formats"
kind: bug
status: closed
priority: 1
version: 3
labels:
  - pr-23-review
dependencies: []
parent_id: is-01kyxb2jmbakcvq711fj9yfdde
created_at: 2026-08-01T00:20:25.272Z
updated_at: 2026-08-01T00:35:43.487Z
closed_at: 2026-08-01T00:35:43.487Z
close_reason: Fixed in 59d2289; full local validation and all 19 PR checks passed.
---
Review issue 2 at packages/typescript/src/compile.ts:128. Decide and implement the clean parity boundary for z.iso.time() and z.iso.duration(), including equivalent Pydantic time and timedelta fields, compiler normalization, canonical sidecar regeneration, digest goldens, and authored-regex preservation.
