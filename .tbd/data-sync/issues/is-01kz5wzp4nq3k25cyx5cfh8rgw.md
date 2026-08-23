---
type: is
id: is-01kz5wzp4nq3k25cyx5cfh8rgw
title: TypeScript deep-nesting parse cost is superlinear
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
created_at: 2026-08-04T08:07:04.084Z
updated_at: 2026-08-22T23:15:15.266Z
closed_at: 2026-08-22T23:15:15.265Z
close_reason: "Obsolete: already resolved by the MAX_DEPTH=64 portability bound, which postdates the PR #27 measurement in this bead. Re-measured on main before closing: a depth-5000 document (~25MB of YAML) parses and is rejected as yaml_limit in 263ms, against the 12.5s recorded here; depth 1000 takes 68ms, so the cost is now linear rather than superlinear. The per-node depth reduce in portable.ts is bounded by MAX_DEPTH, so it can no longer grow with document depth. No code change made."
---
On PR #27 branch, depth 5000 took 12.5s in one validateArtifact call vs 242ms at depth 1000. Follow-up to PR #27.
