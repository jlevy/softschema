---
type: is
id: is-01kx5s2jtk3p7hpympsq3gt07s
title: Make the public conformance namespace truly immutable and release-capable
kind: bug
status: closed
priority: 1
version: 5
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - conformance
  - release
  - security
dependencies:
  - type: blocks
    target: is-01kx4scf42fe327rk346dhd0ym
  - type: blocks
    target: is-01kx5ytgxt6cte9hx68c8y0ez7
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T10:27:21.042Z
updated_at: 2026-07-10T13:10:39.739Z
closed_at: 2026-07-10T11:51:34.550Z
close_reason: Implemented absent-or-exact immutable Pages classification, protected-upstream binding, released-metadata validation, and exact postdeploy verification. Live Pages publication remains ss-6i6d.
---
Before first Pages deployment, require a pre-deploy absent-or-exact live-state classifier so later runs cannot replace or delete /schema/v1 bytes, bind dispatch to the protected upstream main repository, and settle schema titles/manifest constraints so the exact immutable candidate can validate the intended 1.0.0 released/final-identifier kit. Prove initial absence, exact idempotence, conflict rejection, and released-manifest validity before post-deploy byte verification.
