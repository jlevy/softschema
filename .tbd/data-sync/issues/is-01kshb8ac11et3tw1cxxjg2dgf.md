---
type: is
id: is-01kshb8ac11et3tw1cxxjg2dgf
title: Final consistency check after docs restructure
kind: task
status: closed
priority: 2
version: 2
spec_path: docs/project/reviews/review-2026-05-26-softschema-docs-design.md
labels: []
dependencies: []
parent_id: is-01kshb5636qx5g9ha5xaa6b5qb
created_at: 2026-05-26T05:13:54.798Z
updated_at: 2026-05-26T05:53:13.175Z
closed_at: 2026-05-26T05:53:13.174Z
close_reason: completed
---
Run after ss-u07d (spec), ss-hyhu (guide), ss-68a1 (reference cleanup), and ss-qqrj (research move) land. Steps from the review (line 233-241):

rg 'softschema-design|Softschema Design|durable design reference' .
uv run softschema docs --list
uv run softschema docs --list --json
uv run python devtools/lint.py --check
uv run pytest

Plus:
- Verify the trading consumer seam (per ss-tkfe outcome) is honored in the exported public API.
- Verify the CLI bundled docs topics still cover everything the agent skill expects (skill --brief vs docs --list).
- Verify links in docs/, skills/, AGENTS.md, README.md all resolve.

Closes the review-driven cleanup arc.
