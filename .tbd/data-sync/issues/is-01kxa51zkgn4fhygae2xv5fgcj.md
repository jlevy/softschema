---
type: is
id: is-01kxa51zkgn4fhygae2xv5fgcj
title: "PR21 R4: align YAML depth boundaries and hostile-depth errors"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01kxa51ypp776456nxmyd81gps
created_at: 2026-07-12T03:13:41.999Z
updated_at: 2026-07-12T03:27:21.899Z
closed_at: 2026-07-12T03:27:21.898Z
close_reason: "The alleged 64-level divergence did not reproduce: both runtimes reject 64 beneath the root. Shared 63/64/65 vectors pin the boundary, and TypeScript stack overflow now maps to yaml_limit."
---
Use one depth-counting rule at 64/65 and normalize TypeScript parser stack overflow to yaml_limit.
