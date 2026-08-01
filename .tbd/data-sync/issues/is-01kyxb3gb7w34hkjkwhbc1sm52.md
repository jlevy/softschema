---
type: is
id: is-01kyxb3gb7w34hkjkwhbc1sm52
title: "PR #23 review S5: Remove vector-harness assertion precedence"
kind: bug
status: open
priority: 3
version: 1
labels:
  - pr-23-review
dependencies: []
parent_id: is-01kyxb2jmbakcvq711fj9yfdde
created_at: 2026-08-01T00:20:39.397Z
updated_at: 2026-08-01T00:20:39.397Z
---
Review suggestion S5 in both shared-vector harnesses. Assert expected values and expected error codes independently so a malformed vector carrying both cannot silently skip its failure assertion.
