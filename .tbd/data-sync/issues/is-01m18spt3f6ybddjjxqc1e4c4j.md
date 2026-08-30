---
type: is
id: is-01m18spt3f6ybddjjxqc1e4c4j
title: "PR #52 review F1: --repair and validate still disagree on exit class when --contract is supplied"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m18sp5xn5a5kpxza57ts9mbm
created_at: 2026-08-30T07:38:54.446Z
updated_at: 2026-08-30T07:38:54.446Z
---
For the same unreadable file:
  validate f.md --contract t:M/v1                -> exit 2, no stdout
  validate f.md --contract t:M/v1 --check-repair -> exit 1, {"outcome":"invalid", kind: yaml_parse_error}

Pre-existing on origin/main (verified with a worktree), NOT introduced by PR #52. But the PR's stated goal is that the two paths reach the same read verdict, and one flag away they still reach different exit *classes* (cli.py:66 documents 2 = usage error, 1 = validation failure).

The unreadable signal only travels through _missing_contract_reason, which is reached only when --contract is absent.

Needs a maintainer decision on which class is correct. Recommendation: the --check-repair behavior (exit 1 + structured record) is the better one, since a structured record is what a producing agent can act on; plain validate is the path that should move. That is a behavior change to the flagship command, so it should not be made unilaterally right before a release.

Files: packages/python/src/softschema/cli.py, packages/typescript/src/cli.ts
