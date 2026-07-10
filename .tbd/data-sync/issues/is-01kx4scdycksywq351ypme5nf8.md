---
type: is
id: is-01kx4scdycksywq351ypme5nf8
title: Expose pure-yaml validation through both CLIs
kind: feature
status: open
priority: 2
version: 1
labels:
  - cli
  - parity
dependencies: []
parent_id: is-01kx4sb8zsz0vfdry39n0bqcdd
created_at: 2026-07-10T01:13:29.291Z
updated_at: 2026-07-10T01:13:29.291Z
---
Both libraries support the pure-yaml profile but both CLIs hardcode frontmatter-md, making a normative profile unreachable to normal users. Add a symmetric profile option or a carefully specified inference rule, a public example, and shared golden coverage.
