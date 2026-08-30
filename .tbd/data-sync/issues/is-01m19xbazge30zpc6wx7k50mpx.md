---
type: is
id: is-01m19xbazge30zpc6wx7k50mpx
title: "Golden: rename validate-repair.tryscript.md to repair.tryscript.md and rewrite its commands"
kind: task
status: open
priority: 1
version: 2
labels: []
dependencies:
  - type: blocks
    target: is-01m19xbbdmcv1rsdh9s0x2fpq3
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:47.248Z
updated_at: 2026-08-30T18:02:42.774Z
---
tests/golden/scenarios/

Every journey invokes 'validate --repair' or 'validate --check-repair' and must become 'repair', 'repair --check', or 'repair --dry-run'. Add a journey for --dry-run, which has no coverage today because the flag does not exist.

The journey 'the two flags are mutually exclusive' becomes the --dry-run/--check exclusion.

Keep the two end-of-file fence journeys and the unterminated-fence journey intact -- they pin real regressions.

Add a journey pinning the strict/checking split: the same unreadable file under validate (exit 2, one line) and under repair (exit 1, record). That is the F1 divergence, now pinned rather than latent.

Run on Python, Node, and Bun.
