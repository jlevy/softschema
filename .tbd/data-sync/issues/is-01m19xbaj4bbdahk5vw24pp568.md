---
type: is
id: is-01m19xbaj4bbdahk5vw24pp568
title: "TypeScript: unit coverage for the new surface and both leak fixes"
kind: task
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:46.820Z
updated_at: 2026-08-30T18:42:16.855Z
closed_at: 2026-08-30T18:42:16.855Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
packages/typescript/test/repair-profile-detection.test.ts (rename to repair-command.test.ts if it grows past profile detection) plus a new file if cleaner. Same case list as the Python bead, same pre-change-failure verification.
