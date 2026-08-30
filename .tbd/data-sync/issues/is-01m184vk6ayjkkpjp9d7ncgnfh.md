---
type: is
id: is-01m184vk6ayjkkpjp9d7ncgnfh
title: Open the PR for the repair end-to-end fix
kind: task
status: in_progress
priority: 2
version: 2
spec_path: docs/project/reviews/review-2026-08-30-validate-repair-e2e.md
labels: []
dependencies: []
parent_id: is-01m184s19wd17m979jyyh4fzez
created_at: 2026-08-30T01:34:31.114Z
updated_at: 2026-08-30T01:53:11.624Z
---
Open the pull request from `claude/release-readiness-review-0pfteg` once every sibling
is closed and the full local sweep is green.

Before opening: `make lint-check`, `uv run pytest`, `bun test --coverage`,
`bun run typecheck`, `bun run lint:ci`, `bun run build`, the golden corpus on all three
runtimes, `cross-impl-diff.sh`, and `make format-check` — all exit 0.

Body: the defect and why it mattered, the fix, the regression coverage and why a golden
case rather than a parity check, and the runbook with its recorded results. Check for a
PR template first.

Watch CI to green before reporting done.
