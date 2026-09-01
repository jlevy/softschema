---
type: is
id: is-01m18sptr5svfcbcvb2mxcmpkb
title: "PR #52 review F3: the new golden journey does not pin the cause its prose claims"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m18sp5xn5a5kpxza57ts9mbm
created_at: 2026-08-30T07:38:55.109Z
updated_at: 2026-08-30T07:55:15.870Z
closed_at: 2026-08-30T07:55:15.870Z
close_reason: "Fixed on claude/senior-engineering-review-h24e5m (b70010a, 12ef4ed). F2 turned out to be a live defect, not latent: --repair silently skipped any artifact whose closing fence was the file's last byte. Covered by 3 Python + 3 TypeScript cases, each verified to fail pre-fix, plus a golden journey on all three runtimes."
resolution: null
duplicate_of: null
---
tests/golden/scenarios/validate-repair.tryscript.md, journey 'an unterminated frontmatter fence is unreadable on both paths'. The plain-validate assertion is 'softschema validate: [..]', which by this corpus's own convention (cli-errors.tryscript.md:50-52) asserts the stable prefix only and matches ANY usage error.

The journey's prose says both paths 'name the same cause', but only the --check-repair line pins a cause. Regress the plain path to a different message and the journey stays green.

Blocked on F4: the reason it cannot be tightened today is that the two CLIs word the message differently.
