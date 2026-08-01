---
type: is
id: is-01kyxb3f3f52h5ssas9g75d5cg
title: "PR #23 review S1: Reassess host-value error taxonomy"
kind: bug
status: open
priority: 3
version: 1
labels:
  - pr-23-review
dependencies: []
parent_id: is-01kyxb2jmbakcvq711fj9yfdde
created_at: 2026-08-01T00:20:38.126Z
updated_at: 2026-08-01T00:20:38.126Z
---
Review suggestion S1 at both portable-value guards. Determine whether a new public error kind is clearer than yaml_unsupported_scalar for programmatic host objects. Fix only if it improves the API without creating a misleading cross-runtime distinction; otherwise record a technical rebuttal.
