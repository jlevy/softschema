---
type: is
id: is-01m19xaj0ps205t2s00bdnaejc
title: "Python: make strict-versus-checking a property of the command"
kind: bug
status: open
priority: 1
version: 4
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
updated_at: 2026-08-30T18:02:43.086Z
---
packages/python/src/softschema/cli.py

Leak 1 -- validate must be strict about reads regardless of --contract. Today _read_artifact is only reached when binding inference needs the document; pass --contract and an unreadable file falls through to the verdict path and exits 1 with a yaml_parse_error record instead of exiting 2. Perform the strict read unconditionally.

Leak 2 -- repair must report rather than raise. Today _infer_validation_binding raises UsageError('missing --contract because the document could not be read: ...') when repair could not rescue the document. That advises a flag that would not have helped. Emit the result carrying the read-failure record instead, exit 1. The pipeline already produces exactly that shape when a contract is supplied.

_missing_contract_reason loses its parse_error parameter once leak 2 is closed -- that argument exists only to word the message this change removes.

Spec D3, D4.
