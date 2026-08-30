---
type: is
id: is-01m19xagy48cpx37h2ph4d1w2g
title: "Python: add the repair command, remove --repair/--check-repair from validate"
kind: feature
status: open
priority: 1
version: 3
labels: []
dependencies:
  - type: blocks
    target: is-01m19xaj0ps205t2s00bdnaejc
  - type: blocks
    target: is-01m19xcybzz5zcr27y96q1vq5w
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:20.579Z
updated_at: 2026-08-30T18:02:44.152Z
---
packages/python/src/softschema/cli.py

Add a 'repair' subcommand:
  softschema repair <path>              repair, conform, write, validate   exit 0 if valid
  softschema repair <path> --dry-run    same, no write                     exit 0 if valid
  softschema repair <path> --check      same, no write                     exit 1 if anything would change

--dry-run and --check are mutually exclusive; use argparse add_mutually_exclusive_group rather than a hand-rolled check (the current --repair/--check-repair exclusion is hand-rolled in _validate_cmd).

Remove --repair and --check-repair from the validate subparser. _repair_validate_cmd becomes _repair_cmd; the write flag comes from the absence of --dry-run/--check, and the strict pass condition from --check.

Reuse repair_and_validate_artifact unchanged. Spec D1, D2, D4.
