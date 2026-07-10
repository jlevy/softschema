---
type: is
id: is-01kx5z0gv8d14ef9gd7exwpyg2
title: Separate release-candidate versions from verified bootstrap pins
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - release
  - agents
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:11:04.935Z
updated_at: 2026-07-10T12:11:04.935Z
---
release.py enforces bootstrap pin == candidate version while public skills/docs consume those pins, so merging a release candidate advertises packages that do not exist yet and can remain poisoned after a partial failure. Keep discovery/bootstrap pins on the last registry-verified release through candidate publication, separate candidate artifact coordinates, and advance public pins only after exact post-publish verification.
