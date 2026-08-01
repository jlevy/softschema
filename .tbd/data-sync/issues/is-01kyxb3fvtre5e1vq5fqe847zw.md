---
type: is
id: is-01kyxb3fvtre5e1vq5fqe847zw
title: "PR #23 review S4: Make Zod compiler coupling explicit"
kind: bug
status: open
priority: 3
version: 1
labels:
  - pr-23-review
dependencies: []
parent_id: is-01kyxb2jmbakcvq711fj9yfdde
created_at: 2026-08-01T00:20:38.904Z
updated_at: 2026-08-01T00:20:38.904Z
---
Review suggestion S4 at packages/typescript/src/compile.ts:130. Reduce or explicitly document reliance on Zod internals, retain upgrade regression coverage, and record why removing a duplicate authored regex with the exact intrinsic source is semantically harmless.
