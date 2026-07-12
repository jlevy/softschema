---
type: is
id: is-01kx9qda5nktgj47m9c54mreg5
title: "Step 11: Build once and smoke exact release artifacts"
kind: task
status: in_progress
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-07-11-minimal-softschema-hardening.md
labels:
  - release
  - security
dependencies:
  - type: blocks
    target: is-01kx9qdacvke94atjyj3e8qvvc
  - type: blocks
    target: is-01kx9qdakxzyp25ef7kyyd0xnr
parent_id: is-01kx9n8xq83ng2r748pfrtd88e
created_at: 2026-07-11T23:15:13.204Z
updated_at: 2026-07-12T02:00:26.332Z
---
Simplify CI and publication around frozen installs, reviewed SHA-pinned actions, an unprivileged build-once job for wheel/sdist/npm tarball, checksums, and exact transferred-artifact smoke on supported operating systems before protected OIDC publication. Do not add a registry state machine, frozen driver, recovery bundle, Pages flow, or custom archive verifier. Acceptance: dry-run cannot publish, pull-request jobs lack authority, and the exact packages install/import/run outside the checkout.
