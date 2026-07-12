---
type: is
id: is-01kx9n8xq83ng2r748pfrtd88e
title: "Spec: Minimal softschema hardening"
kind: epic
status: closed
priority: 1
version: 18
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - hardening
  - simplification
  - parity
dependencies: []
child_order_hints:
  - is-01kx9qc63sd4avxxp4h7ekev8q
  - is-01kx9qd83rhjpngwe7qkpdzqff
  - is-01kx9qd8axb257dq5xv38m5jt2
  - is-01kx9qd8j23ketnj5n06a91vfd
  - is-01kx9qd8s60k7jatjnny0h4w9c
  - is-01kx9qd90cbxf7bp9c208xtjkh
  - is-01kx9qd97f0ekaq63mrc8f9f0z
  - is-01kx9qd9ghwrm3avgkg2vdf0fj
  - is-01kx9qd9qmjfhmv9egzc34rwtj
  - is-01kx9qd9yk32j1nm52mmnrrffh
  - is-01kx9qda5nktgj47m9c54mreg5
  - is-01kx9qdacvke94atjyj3e8qvvc
  - is-01kx9qdakxzyp25ef7kyyd0xnr
  - is-01kx9qdatz2pmwz6r61kw4czdp
created_at: 2026-07-11T22:37:52.231Z
updated_at: 2026-07-12T03:11:57.766Z
closed_at: 2026-07-12T03:11:57.766Z
close_reason: All minimal-hardening implementation beads and final review are complete; production growth is 947 lines, the golden system is smaller, and all local release gates pass.
---
Implement the clean main-based hard-cut minor release in docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md. Preserve useful capabilities while replacing incorrect surfaces once, close the 24 applicable defect categories, exclude the 12 discarded platform categories, keep tests minimal with one primary owner per behavior, and enforce the production complexity budget.
