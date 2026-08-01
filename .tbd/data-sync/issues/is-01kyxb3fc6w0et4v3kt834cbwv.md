---
type: is
id: is-01kyxb3fc6w0et4v3kt834cbwv
title: "PR #23 review S2: Explain ruamel constructor registry isolation"
kind: bug
status: closed
priority: 3
version: 3
labels:
  - pr-23-review
dependencies: []
parent_id: is-01kyxb2jmbakcvq711fj9yfdde
created_at: 2026-08-01T00:20:38.405Z
updated_at: 2026-08-01T00:35:43.513Z
closed_at: 2026-08-01T00:35:43.513Z
close_reason: Fixed in 59d2289; full local validation and all 19 PR checks passed.
---
Review suggestion S2 at packages/python/src/softschema/_portable.py:33. Put the concise code comment on the non-obvious registry-copy isolation property rather than only documenting the obvious node.value return.
