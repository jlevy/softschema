---
type: is
id: is-01kxa6cjnd2t1npvzgpnm4p16y
title: "PR21: satisfy protected cross-platform artifact smoke contexts"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
created_at: 2026-07-12T03:36:57.773Z
updated_at: 2026-07-12T06:33:08.193Z
closed_at: 2026-07-12T06:33:08.192Z
close_reason: The same transferred wheel, sdist, and npm tarball now pass all six protected Ubuntu/macOS/Windows runtime contexts without duplicate builds; the ruleset remains unchanged.
---
The simplified reusable smoke passes but its prefixed check name does not satisfy the six active main-ruleset Artifact smoke contexts. Add six lightweight OS/runtime consumers of the same transferred candidates; do not duplicate builds or weaken the ruleset.
