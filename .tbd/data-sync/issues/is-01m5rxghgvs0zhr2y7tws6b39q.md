---
type: is
id: is-01m5rxghgvs0zhr2y7tws6b39q
title: "PR #64 A11: suggestion: raise zod declared floor to ^4.6.6 with the lockfile bump; Reviewed-by trailer"
kind: bug
status: open
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5rxgc8kdy9fz5wgg3ew5vsq
created_at: 2026-10-25T06:56:01.563Z
updated_at: 2026-10-25T07:14:43.105Z
---
Suggestion. packages/typescript/package.json:68. The zod bump is a later commit by the coordinator after the cool-off.
PR #64. Review A: https://github.com/jlevy/softschema/pull/64#pullrequestreview-5641911619

## Notes

deferred: the zod bump is a later commit on this PR by the coordinator after the 14-day cool-off (2026-10-25T16:18Z); that commit should raise the declared floor in packages/typescript/package.json to ^4.6.6 alongside the lockfile. The Reviewed-by vs Security-exception-approved-by trailer on 6aa3cb9 is declined: it would take a history rewrite, and the squash merge (ss-1azo) replaces the message anyway.
