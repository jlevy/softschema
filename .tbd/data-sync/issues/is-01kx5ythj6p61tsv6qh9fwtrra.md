---
type: is
id: is-01kx5ythj6p61tsv6qh9fwtrra
title: Remove shell-special placeholders from publishing commands
kind: bug
status: open
priority: 2
version: 1
spec_path: docs/project/specs/active/plan-2026-07-09-softschema-hardening-and-conformance.md
labels:
  - docs
  - release
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T12:07:49.061Z
updated_at: 2026-07-10T12:07:49.061Z
---
docs/publishing.md uses <run-id> in a copyable shell command, which is parsed as redirection. Replace it with a defined or clearly assigned shell variable and verify other new copyable commands.
