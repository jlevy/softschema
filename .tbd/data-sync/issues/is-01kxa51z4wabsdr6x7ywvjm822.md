---
type: is
id: is-01kxa51z4wabsdr6x7ywvjm822
title: "PR21 R2: normalize invalid timestamp constructor errors"
kind: bug
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01kxa51ypp776456nxmyd81gps
created_at: 2026-07-12T03:13:41.531Z
updated_at: 2026-07-12T03:27:21.505Z
closed_at: 2026-07-12T03:27:21.505Z
close_reason: Both parsers reject plain timestamp-shaped scalars before construction; invalid dates return yaml_unsupported_scalar instead of escaping ValueError.
---
Prevent Python ruamel timestamp construction ValueError from escaping and align the portable unsupported-scalar result with TypeScript.
