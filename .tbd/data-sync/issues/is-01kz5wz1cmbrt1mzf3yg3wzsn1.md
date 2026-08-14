---
type: is
id: is-01kz5wz1cmbrt1mzf3yg3wzsn1
title: "PR #27: spec documents removed limits (docs/softschema-spec.md:113-116)"
kind: bug
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01kz5wz06084fc4q0badsavagv
created_at: 2026-08-04T08:06:42.835Z
updated_at: 2026-08-04T08:15:39.272Z
closed_at: 2026-08-04T08:15:39.272Z
close_reason: "Spec rewritten: states the depth rule and that input/scalar/node size are unbounded."
---
Normative spec still states 1 MiB input, 256 KiB scalar, 100000 nodes, 64 open collections, and stack-overflow mapping to yaml_limit. Contradicts PR body claim that nothing documents a size limit. (PR #27)
