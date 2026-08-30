---
type: is
id: is-01m19xaj0ps205t2s00bdnaejc
title: "Python: make strict-versus-checking a property of the command"
kind: bug
status: closed
priority: 1
version: 6
labels: []
dependencies:
  - type: blocks
    target: is-01m19xba51hdfg7gsrqksqy3ft
  - type: blocks
    target: is-01m19xbazge30zpc6wx7k50mpx
  - type: blocks
    target: is-01m19xc7rq9gevsfm3851bv56j
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:21.686Z
updated_at: 2026-08-30T18:42:16.831Z
closed_at: 2026-08-30T18:42:16.831Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
packages/python/src/softschema/cli.py

CORRECTION (2026-08-30): the review originally described two leaks. Verified against origin/main: only one is real.

NOT a leak -- validate was already strict. _read_artifact is called unconditionally in _validate_cmd, so 'validate <unreadable> --contract X' exits 2 on main, same as without the flag. The original table misread the '--check-repair --contract' row as a 'validate --contract' row. Nothing to fix; add a test pinning the strictness, which was never pinned.

REAL -- repair must report rather than raise. _infer_validation_binding raises UsageError('missing --contract because the document could not be read: ...') when repair could not rescue the document. That advises a flag that would not have helped. Emit a result carrying the read-failure record instead, exit 1.

Because Contract requires a well-formed ID and an unreadable document declares none, this needs a contract-free failure result: validate.unreadable_artifact_result(). _missing_contract_reason loses its parse_error parameter; _parse_after_repair keeps returning the error, now to name the cause in the record rather than to word a usage message.

Spec D3, D4.
