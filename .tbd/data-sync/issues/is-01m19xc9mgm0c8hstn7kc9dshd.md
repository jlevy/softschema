---
type: is
id: is-01m19xc9mgm0c8hstn7kc9dshd
title: "Docs: CHANGELOG and README"
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies:
  - type: blocks
    target: is-01m19xcacbe2bz4n54qcjeh34c
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:18.640Z
updated_at: 2026-08-30T18:42:16.871Z
closed_at: 2026-08-30T18:42:16.871Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
CHANGELOG.md -- the unreleased 'softschema validate --repair' section documents the retired surface, including the three-line command block. Since the feature is unreleased, describe the final surface rather than recording a rename: there is no released version that had the old flags.

README.md -- check the quickstart and feature list for flag mentions; only one prose 'repair' mention today, but confirm after the surface lands.
