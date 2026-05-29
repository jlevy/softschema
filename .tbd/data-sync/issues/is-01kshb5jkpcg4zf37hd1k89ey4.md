---
type: is
id: is-01kshb5jkpcg4zf37hd1k89ey4
title: Decide fate of docs/softschema-design.md (delete, tombstone, or keep)
kind: task
status: closed
priority: 1
version: 3
spec_path: docs/project/reviews/review-2026-05-26-softschema-docs-design.md
labels: []
dependencies:
  - type: blocks
    target: is-01kshb7m8fb7a0bcegmqp2c1vj
parent_id: is-01kshb5636qx5g9ha5xaa6b5qb
created_at: 2026-05-26T05:12:24.907Z
updated_at: 2026-05-26T05:53:10.290Z
closed_at: 2026-05-26T05:53:10.285Z
close_reason: completed
---
The active public-readiness plan (line 122) says: 'For now, do not add a standalone language-neutral docs/softschema-design.md. The durable public docs are the guide and spec.' The file was nevertheless created (and recently trimmed from ~1041 to ~853 lines).

Options:
(a) Delete the file. Extract any unique still-useful rationale into the active plan first. Recommended by the review and consistent with both the public-readiness plan and the trading-adoption plan.
(b) Replace with a short tombstone pointing to guide, spec, python-design, and active plan. Preserves a breadcrumb but adds noise to the docs/ root.
(c) Keep it, and update the public-readiness plan to allow it.

Recommend (a). The CLI does not currently bundle this file (cli.py:44 bundles only softschema-python-design.md), so deletion has no install-surface impact.

Blocks ss-* T3 (cleanup of references in README/AGENTS/SKILL/CLI).
