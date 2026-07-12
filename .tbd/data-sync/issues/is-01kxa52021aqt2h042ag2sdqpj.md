---
type: is
id: is-01kxa52021aqt2h042ag2sdqpj
title: "PR21 R6: make CLI input_error boundary real and single-read"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01kxa51ypp776456nxmyd81gps
created_at: 2026-07-12T03:13:42.464Z
updated_at: 2026-07-12T03:13:42.464Z
---
Remove the CLI pre-read/validation double-read mismatch so actual input failures follow the documented structured outcome and exit contract.
