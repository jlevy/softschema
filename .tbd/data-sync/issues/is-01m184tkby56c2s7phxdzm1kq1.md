---
type: is
id: is-01m184tkby56c2s7phxdzm1kq1
title: "Golden journey case: validate and --repair agree on an unreadable document"
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/reviews/review-2026-08-30-validate-repair-e2e.md
labels: []
dependencies:
  - type: blocks
    target: is-01m184vk6ayjkkpjp9d7ncgnfh
parent_id: is-01m184s19wd17m979jyyh4fzez
created_at: 2026-08-30T01:33:58.526Z
updated_at: 2026-08-30T01:44:30.327Z
closed_at: 2026-08-30T01:44:30.326Z
close_reason: "Added tests/golden/fixtures/repair-unterminated-fence.md and a 'Journey: an unterminated frontmatter fence is unreadable on both paths' transcript to validate-repair.tryscript.md, pinning that plain validate and --check-repair both refuse the document, that --check-repair names the read failure rather than claiming there is no frontmatter, and that the file is left byte-identical. Corpus now 71 Python / 69 Node / 71 Bun (was 68/66/68)."
resolution: null
duplicate_of: null
---
Add a transparent-box transcript case covering the divergence, so the corpus runs it
against Python, Node, and Bun on every CI run.

Extend `tests/golden/scenarios/validate-repair.tryscript.md` (or add a sibling
scenario) with a journey that:

- validates a document whose frontmatter fence is opened and never closed, and shows
  the frontmatter delimiter error and its exit code;
- runs `--check-repair` on the same document and shows it reporting the *same* failure
  rather than a verdict;
- confirms the file is unchanged afterward.

Fixtures go in `tests/golden/fixtures/`, following the existing `repair-*.md` naming.

This case exists specifically because cross-implementation parity cannot see this class
of defect: both runtimes were wrong in the same direction, so the parity diff stayed
clean. The golden corpus pins the expected verdict rather than comparing the two
implementations to each other.
