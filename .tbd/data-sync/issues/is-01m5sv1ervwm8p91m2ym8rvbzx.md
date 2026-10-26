---
type: is
id: is-01m5sv1ervwm8p91m2ym8rvbzx
title: "PR #64 D4: escape C0/C1/DEL in paths in one shared helper in both runtimes"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T15:32:04.507Z
updated_at: 2026-10-25T16:25:56.976Z
closed_at: 2026-10-25T16:25:56.976Z
close_reason: "Fixed in 04b6c3e (PR #64): document_label/documentLabel is the one helper every document-naming message uses in both runtimes; C0/C1/DEL in a path are written as #xHHHH. Unit test per runtime with an OSC/clear-line/CR/LF filename, plus an end-to-end validate record check."
resolution: null
duplicate_of: null
---
Low. Shared helper + unit vector.
