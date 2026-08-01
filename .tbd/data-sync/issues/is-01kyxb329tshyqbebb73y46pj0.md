---
type: is
id: is-01kyxb329tshyqbebb73y46pj0
title: "PR #23 review I1: Reject every non-plain TypeScript host object"
kind: bug
status: closed
priority: 1
version: 3
labels:
  - pr-23-review
dependencies: []
parent_id: is-01kyxb2jmbakcvq711fj9yfdde
created_at: 2026-08-01T00:20:25.017Z
updated_at: 2026-08-01T00:35:43.476Z
closed_at: 2026-08-01T00:35:43.476Z
close_reason: Fixed in 59d2289; full local validation and all 19 PR checks passed.
---
Review issue 1 at packages/typescript/src/portable.ts:157. Replace the Date-only guard with a plain-object prototype gate so Map, Set, RegExp, Error, URL, class instances, Date, and other host objects cannot silently serialize as empty mappings through softFieldMeta. Preserve arrays and null-prototype plain mappings. Add focused regression coverage and align the error message with the portable domain.
