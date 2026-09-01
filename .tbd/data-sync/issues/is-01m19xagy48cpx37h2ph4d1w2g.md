---
type: is
id: is-01m19xagy48cpx37h2ph4d1w2g
title: "Python: add the repair command, remove --repair/--check-repair from validate"
kind: feature
status: closed
priority: 1
version: 5
labels: []
dependencies:
  - type: blocks
    target: is-01m19xaj0ps205t2s00bdnaejc
  - type: blocks
    target: is-01m19xcybzz5zcr27y96q1vq5w
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:20.579Z
updated_at: 2026-08-30T18:42:16.819Z
closed_at: 2026-08-30T18:42:16.819Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
packages/python/src/softschema/cli.py

Add a 'repair' subcommand:
  softschema repair <path>              repair, conform, write, validate   exit 0 if valid
  softschema repair <path> --dry-run    same, no write                     exit 0 if valid
  softschema repair <path> --check      same, no write                     exit 1 if anything would change

Remove --repair and --check-repair from the validate subparser. _repair_validate_cmd becomes _repair_cmd; write comes from the absence of --dry-run/--check, and the strict pass condition from --check. Reuse repair_and_validate_artifact unchanged.

CORRECTION (2026-08-30): keep the --dry-run/--check exclusion HAND-ROLLED, not argparse add_mutually_exclusive_group. Tried the group first; its message is argparse's own (a usage block plus 'argument --check: not allowed with argument --dry-run') and Commander cannot reproduce it, so the two CLIs would word softschema's own diagnostic differently -- the exact parity defect fixed for the delimiter message in F4. Hand-rolled gives both 'softschema repair: --dry-run and --check are mutually exclusive', which the golden corpus asserts in full.

Also required, found while implementing: map CommanderError to exit 2 in the TypeScript CLI. Commander's default for a usage error is 1, which is this CLI's 'validation failed' class; argparse gives 2. With --repair now a retired flag, users hit this, and the two CLIs must agree.

Spec D1, D2, D4.
