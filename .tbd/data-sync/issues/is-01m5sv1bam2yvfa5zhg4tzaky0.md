---
type: is
id: is-01m5sv1bam2yvfa5zhg4tzaky0
title: "PR #64 B5: squash-merge message must be set explicitly (COMMIT_MESSAGES default leaks 9decf4c body)"
kind: task
status: closed
priority: 2
version: 3
labels: []
dependencies: []
parent_id: is-01m5sv19k45mwdvz50km55ehc0
created_at: 2026-10-25T15:32:00.979Z
updated_at: 2026-10-26T01:37:08.895Z
closed_at: 2026-10-26T01:37:08.894Z
close_reason: "#64 squash-merged as d23718b with an explicit subject/body; the merge commit message names no private contract ID or repository (checked by grep)."
resolution: null
duplicate_of: null
---
Medium. Coordinator/owner does the merge with explicit --subject/--body-file; grep merge commit before closing ss-1azo/ss-r30w.

## Notes

Acknowledged in PR #64 round 2: the coordinator/owner performs the squash merge with an explicit --subject and --body-file; grep the merge commit message afterwards before closing ss-1azo and ss-r30w. Not an addressing-agent change.
