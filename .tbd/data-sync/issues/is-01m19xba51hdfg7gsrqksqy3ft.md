---
type: is
id: is-01m19xba51hdfg7gsrqksqy3ft
title: "Python: unit coverage for the new surface and both leak fixes"
kind: task
status: open
priority: 1
version: 1
labels: []
dependencies: []
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:46.400Z
updated_at: 2026-08-30T18:01:46.400Z
---
packages/python/tests/test_cli.py

- repair writes; repair --dry-run does not and exits on the outcome; repair --check does not and exits 1 when anything would change
- --dry-run and --check are mutually exclusive
- validate no longer accepts --repair or --check-repair
- leak 1: validate on an unreadable file exits 2 both with and without --contract
- leak 2: repair on a document it cannot rescue emits a record and exits 1, with no mention of --contract in the message
- load_artifact returns values on valid and raises on invalid

Each leak-fix case must be verified to fail against the pre-change code, per the house standard used for the profile-detection fix.
