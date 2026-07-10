---
type: is
id: is-01kx5ptpjcm7jjn4metv5k89tv
title: Implement idempotent release state machines and draft-asset DAG
kind: task
status: closed
priority: 1
version: 12
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - security
  - ci
dependencies:
  - type: blocks
    target: is-01kx4w3nh1qz49ffey0dgewxp7
  - type: blocks
    target: is-01kx5v1ydg4ezt3pqwzhyvb61g
  - type: blocks
    target: is-01kx5s2k0yz7q21ektrcfwkd75
  - type: blocks
    target: is-01kx61q0qzxs2fmd6s611tzaex
  - type: blocks
    target: is-01kx5z48hxmnpcppgsdqsw2d71
  - type: blocks
    target: is-01kx5zke9t67v3f8er7xneqnd9
  - type: blocks
    target: is-01kx5ykt391hx5vkz58cg62hve
  - type: blocks
    target: is-01kx5yx7khf13yny65c58c1jj5
  - type: blocks
    target: is-01kx5z0gv8d14ef9gd7exwpyg2
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T09:48:05.579Z
updated_at: 2026-07-10T13:10:41.433Z
closed_at: 2026-07-10T11:51:32.541Z
close_reason: Implemented and tested the code-side manifest-driven release DAG, exact state classifiers, provenance gates, and immutable-release preflight. Live authorization/publication remains in ss-0rqn and ss-trn7.
---
Implement and test the code-side 0.3 release protocol without performing a live publication: standalone no-checkout registry/GitHub state classifiers; exact absent/same/partial/conflict behavior; primary-subject checksums and release index; draft GitHub asset plus actions/attest provenance stage; conditional PyPI/npm uploads; final release only after registry verification; and post-publish verification hooks. Privileged jobs must consume manifest-verified frozen bytes, resolve no dependencies, and never rebuild. This bead deliberately excludes authenticated publisher configuration, tag creation, merge, and live publication, which remain ss-0rqn/ss-trn7.
