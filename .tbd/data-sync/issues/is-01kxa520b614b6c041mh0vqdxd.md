---
type: is
id: is-01kxa520b614b6c041mh0vqdxd
title: "PR21 R7: validate all portable schema regex positions eagerly"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01kxa51ypp776456nxmyd81gps
created_at: 2026-07-12T03:13:42.757Z
updated_at: 2026-07-12T03:27:22.432Z
closed_at: 2026-07-12T03:27:22.431Z
close_reason: Both validators eagerly subset-check and compile pattern plus every patternProperties key, with shared schema_invalid reason=pattern vectors.
---
Check pattern and patternProperties keys eagerly in both runtimes, align invalid-regex classification, and add shared vectors.
