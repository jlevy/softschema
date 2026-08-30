---
type: is
id: is-01m19xbaj4bbdahk5vw24pp568
title: "TypeScript: unit coverage for the new surface and both leak fixes"
kind: task
status: open
priority: 1
version: 1
labels: []
dependencies: []
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:01:46.820Z
updated_at: 2026-08-30T18:01:46.820Z
---
packages/typescript/test/repair-profile-detection.test.ts (rename to repair-command.test.ts if it grows past profile detection) plus a new file if cleaner. Same case list as the Python bead, same pre-change-failure verification.
