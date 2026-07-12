---
type: is
id: is-01kxa51zc6yy1p8jzarev03fc5
title: "PR21 R3: canonicalize large integral floats portably"
kind: bug
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01kxa51ypp776456nxmyd81gps
created_at: 2026-07-12T03:13:41.765Z
updated_at: 2026-07-12T03:27:21.701Z
closed_at: 2026-07-12T03:27:21.700Z
close_reason: Python large integral floats now use shortest round-trip decimal spelling; shared digest parity passes and arbitrary-precision unsafe integers are rejected.
---
Align canonical JSON and schema digests for integral floats above 2^53 and reject nonportable compiler values at the boundary.
