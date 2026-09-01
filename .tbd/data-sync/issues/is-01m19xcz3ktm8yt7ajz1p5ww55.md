---
type: is
id: is-01m19xcz3ktm8yt7ajz1p5ww55
title: "Enforce the retired surface: lint check for --check-repair"
kind: task
status: closed
priority: 1
version: 2
labels: []
dependencies: []
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:40.627Z
updated_at: 2026-08-30T18:42:16.878Z
closed_at: 2026-08-30T18:42:16.878Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
devtools/lint.py

Fail the check if '--check-repair', 'checkRepair', or 'check_repair' appears anywhere outside docs/project/reviews/ (historical records legitimately name it) and outside gitignored run output (tests/manual/agent-repair/results-*.json).

The file already has bespoke checks -- see the 'check doc footers' pass -- so there is a place to hang this.

This is what makes the removal enforced rather than hoped for: the surface appeared in 20+ files across source, tests, docs, skills and generated mirrors, and a grep-based gate is the only thing that keeps a stale one from reappearing in a mirror or a resource copy. Spec D6.
