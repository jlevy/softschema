---
type: is
id: is-01m19xcz3ktm8yt7ajz1p5ww55
title: "Enforce the retired surface: lint check for --check-repair"
kind: task
status: open
priority: 1
version: 1
labels: []
dependencies: []
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:40.627Z
updated_at: 2026-08-30T18:02:40.627Z
---
devtools/lint.py

Fail the check if '--check-repair', 'checkRepair', or 'check_repair' appears anywhere outside docs/project/reviews/ (historical records legitimately name it) and outside gitignored run output (tests/manual/agent-repair/results-*.json).

The file already has bespoke checks -- see the 'check doc footers' pass -- so there is a place to hang this.

This is what makes the removal enforced rather than hoped for: the surface appeared in 20+ files across source, tests, docs, skills and generated mirrors, and a grep-based gate is the only thing that keeps a stale one from reappearing in a mirror or a resource copy. Spec D6.
