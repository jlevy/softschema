---
type: is
id: is-01m19xajct4hafm1daa780pfpj
title: "TypeScript: make strict-versus-checking a property of the command"
kind: bug
status: open
priority: 1
version: 4
labels: []
dependencies:
  - type: blocks
    target: is-01m19xbaj4bbdahk5vw24pp568
  - type: blocks
    target: is-01m19xbazge30zpc6wx7k50mpx
  - type: blocks
    target: is-01m19xc7rq9gevsfm3851bv56j
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:22.074Z
updated_at: 2026-08-30T18:02:43.093Z
---
packages/typescript/src/cli.ts

Same two leaks as the Python bead, same fixes: readArtifact runs unconditionally for validate; runRepair emits the read-failure record instead of throwing UsageError. missingContractReason loses its parseError parameter.

Spec D3, D4.
