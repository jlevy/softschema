---
type: is
id: is-01m19xahh31yvdk9arvvjt1qyp
title: "TypeScript: add the repair command, remove --repair/--check-repair from validate"
kind: feature
status: open
priority: 1
version: 3
labels: []
dependencies:
  - type: blocks
    target: is-01m19xajct4hafm1daa780pfpj
  - type: blocks
    target: is-01m19xcybzz5zcr27y96q1vq5w
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:21.187Z
updated_at: 2026-08-30T18:02:44.159Z
---
packages/typescript/src/cli.ts

Commander mirror of the Python surface. Identical flag names, identical help text, identical exit classes.

Remove the .option('--repair') and .option('--check-repair') from the validate command and the hand-rolled UsageError for their mutual exclusion. runRepairValidate becomes the repair command action.

Spec D1, D2, D4.
