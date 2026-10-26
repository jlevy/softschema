---
type: is
id: is-01m18spt3f6ybddjjxqc1e4c4j
title: "PR #52 review F1: --repair and validate still disagree on exit class when --contract is supplied"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m18sp5xn5a5kpxza57ts9mbm
hold: null
hold_until: null
created_at: 2026-08-30T07:38:54.446Z
updated_at: 2026-10-25T06:26:59.557Z
started_at: 2026-10-25T06:04:17.987Z
closed_at: 2026-10-25T06:26:59.557Z
close_reason: "Already fixed before this work, no code change. Exit class is a property of the command since cdb5ff6 (repair command split, shipped v0.8.0): validate exits 2 on an unreadable file and repair exits 1 with a record, regardless of --contract. Decision recorded in docs/project/specs/done/plan-2026-08-30-repair-command.md (strictness table and D4). Reproduced on this branch for both implementations with frontmatter-md and pure-yaml unreadable files, with and without --contract. Pinned by test_validate_refuses_an_unreadable_artifact_with_or_without_a_contract and test_repair_reports_an_unreadable_artifact_with_or_without_a_contract (packages/python/tests/test_cli.py), the matching tests in packages/typescript/test/repair-command.test.ts, and the golden corpus (cli-errors malformed-frontmatter with --contract exit 2; repair.tryscript.md fence and floor journeys). Spec status/docs updated in febe5a3."
resolution: null
duplicate_of: null
---
For the same unreadable file:
  validate f.md --contract t:M/v1                -> exit 2, no stdout
  validate f.md --contract t:M/v1 --check-repair -> exit 1, {"outcome":"invalid", kind: yaml_parse_error}

Pre-existing on origin/main (verified with a worktree), NOT introduced by PR #52. But the PR's stated goal is that the two paths reach the same read verdict, and one flag away they still reach different exit *classes* (cli.py:66 documents 2 = usage error, 1 = validation failure).

The unreadable signal only travels through _missing_contract_reason, which is reached only when --contract is absent.

Needs a maintainer decision on which class is correct. Recommendation: the --check-repair behavior (exit 1 + structured record) is the better one, since a structured record is what a producing agent can act on; plain validate is the path that should move. That is a behavior change to the flagship command, so it should not be made unilaterally right before a release.

Files: packages/python/src/softschema/cli.py, packages/typescript/src/cli.ts
