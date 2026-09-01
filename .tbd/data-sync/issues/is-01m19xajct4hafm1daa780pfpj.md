---
type: is
id: is-01m19xajct4hafm1daa780pfpj
title: "TypeScript: make strict-versus-checking a property of the command"
kind: bug
status: closed
priority: 1
version: 6
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
updated_at: 2026-08-30T18:42:16.834Z
closed_at: 2026-08-30T18:42:16.834Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
packages/typescript/src/cli.ts

Mirror of the Python bead, including its correction: validate was already strict (readArtifact runs unconditionally), so there is nothing to fix there -- add the pinning test. The real change is runRepair reporting the read failure as a record instead of throwing UsageError, which needs a contract-free failure result mirroring validate.unreadableArtifactResult().

missingContractReason loses its parseError parameter. Spec D3, D4.
