---
type: is
id: is-01kyxb3fktxcp351yjnzgmssm8
title: "PR #23 review S3: Simplify Python native-date type check"
kind: bug
status: open
priority: 3
version: 1
labels:
  - pr-23-review
dependencies: []
parent_id: is-01kyxb2jmbakcvq711fj9yfdde
created_at: 2026-08-01T00:20:38.649Z
updated_at: 2026-08-01T00:20:38.649Z
---
Review suggestion S3 at packages/python/src/softschema/_portable.py:140. Use the datetime-is-a-date relationship to simplify the type check and imports without changing the user-facing error.
