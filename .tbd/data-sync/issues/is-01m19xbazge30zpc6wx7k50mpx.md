---
type: is
id: is-01m19xbazge30zpc6wx7k50mpx
title: "Golden: rename validate-repair.tryscript.md to repair.tryscript.md and rewrite its commands"
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies:
  - type: blocks
    target: is-01m19xbbdmcv1rsdh9s0x2fpq3
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:47.248Z
updated_at: 2026-08-30T18:42:16.858Z
closed_at: 2026-08-30T18:42:16.858Z
close_reason: Implemented on claude/senior-engineering-review-h24e5m (cdb5ff6, 9ec17f9). validate/repair split with --dry-run and --check, strictness per command, load_artifact/loadArtifact, enforcement lint, all docs and derived artifacts regenerated, runbook re-run green on all four phases. pytest 243, bun test 240, golden 75/73/75, cross-impl parity OK.
resolution: null
duplicate_of: null
---
tests/golden/scenarios/

Every journey invokes 'validate --repair' or 'validate --check-repair' and must become 'repair', 'repair --check', or 'repair --dry-run'. Add a journey for --dry-run, which has no coverage today because the flag does not exist.

The journey 'the two flags are mutually exclusive' becomes the --dry-run/--check exclusion.

Keep the two end-of-file fence journeys and the unterminated-fence journey intact -- they pin real regressions.

Add a journey pinning the strict/checking split: the same unreadable file under validate (exit 2, one line) and under repair (exit 1, record). That is the F1 divergence, now pinned rather than latent.

Run on Python, Node, and Bun.
