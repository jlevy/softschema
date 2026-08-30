---
type: is
id: is-01m19xba51hdfg7gsrqksqy3ft
title: "Python: unit coverage for the new surface and both leak fixes"
kind: task
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:46.400Z
updated_at: 2026-08-30T18:42:16.842Z
closed_at: 2026-08-30T18:42:16.842Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
packages/python/tests/test_cli.py

- repair writes; repair --dry-run does not and exits on the outcome; repair --check does not and exits 1 when anything would change
- --dry-run and --check are mutually exclusive
- validate no longer accepts --repair or --check-repair
- leak 1: validate on an unreadable file exits 2 both with and without --contract
- leak 2: repair on a document it cannot rescue emits a record and exits 1, with no mention of --contract in the message
- load_artifact returns values on valid and raises on invalid

Each leak-fix case must be verified to fail against the pre-change code, per the house standard used for the profile-detection fix.
