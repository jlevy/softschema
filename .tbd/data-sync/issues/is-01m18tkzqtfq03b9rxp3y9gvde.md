---
type: is
id: is-01m18tkzqtfq03b9rxp3y9gvde
title: "[epic] Cut the v0.8.0 release"
kind: task
status: open
priority: 1
version: 5
labels: []
dependencies: []
child_order_hints:
  - is-01m18tmdyjqjaq8rccb9efxetx
  - is-01m18tme8txpwe63p947qr4x0g
  - is-01m18tmekhg694svqeavjs20sd
  - is-01m18tmexsyfvna9mfce7ztnvj
created_at: 2026-08-30T07:54:50.490Z
updated_at: 2026-08-30T07:55:06.040Z
---
Everything for v0.8.0 is verified and green; this epic covers the mechanical release cut. Evidence: docs/project/reviews/review-2026-08-29-softschema-v080-readiness.md, Status Addendum 2026-08-30.

Verified green on the release candidate tree:
- pytest 234, bun test 231/0 fail
- tsc --noEmit, biome ci, publint all clean
- Golden corpus Python 73 / Node 71 / Bun 73; cross-impl-diff.sh parity OK
- lint.py --check exit 0, make format-check exit 0
- agent-repair runbook, all four phases, against the fixed build: 8/8 repaired unaided,
  408/408 paired records with 0 renames, 11/11 to valid in one round, both regression
  cases correct on Python, Node and Bun

Version call: MINOR (v0.8.0), not a patch. validate gains --repair and --check-repair (a mode that writes the user's file), eight new public symbols per package, and every ArtifactValidationResult grows a repairs field. Backward-compatible in behavior; the only diff against v0.7.0 output is the additive repairs key.

Steps are the child beads. Ordering gotcha for whoever runs it: 'make format' reflows the Markdown the TypeScript package bundles as resources and does NOT refresh those copies, so cross-impl-diff.sh fails on the stale copy until 'bun run --cwd packages/typescript build' runs again. Build after formatting, not before.
