---
type: is
id: is-01kz5wzp4nq3k25cyx5cfh8rgw
title: TypeScript deep-nesting parse cost is superlinear
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-08-04T08:07:04.084Z
updated_at: 2026-08-04T08:07:04.084Z
---
On PR #27 branch, depth 5000 took 12.5s in one validateArtifact call vs 242ms at depth 1000. Follow-up to PR #27.
