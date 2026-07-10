---
type: is
id: is-01kx5ykt391hx5vkz58cg62hve
title: Verify exact npm certificate source identity
kind: bug
status: open
priority: 1
version: 1
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - security
  - release
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:04:08.424Z
updated_at: 2026-07-10T12:04:08.424Z
---
release_state.py accepts the expected npm certificate identity as any raw byte substring, allowing prefix/suffix variants such as an attacker tag suffix. Parse the X.509 identity claim exactly, reject ambiguous or non-exact values, and cover prefix/suffix adversarial cases.
