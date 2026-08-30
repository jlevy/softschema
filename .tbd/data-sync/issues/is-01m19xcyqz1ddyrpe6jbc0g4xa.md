---
type: is
id: is-01m19xcyqz1ddyrpe6jbc0g4xa
title: Re-run the agent-repair runbook end to end against the new surface
kind: task
status: open
priority: 1
version: 1
labels: []
dependencies: []
parent_id: is-01m19x9cxpqdvztd07cf5tthdb
created_at: 2026-08-30T18:02:40.255Z
updated_at: 2026-08-30T18:02:40.255Z
---
All four phases against the rebuilt CLI, with GOOGLE_API_KEY set. The last run (2026-08-30, gemini-2.5-flash at budget 0) gave 8/8 repaired unaided, 408/408 exactly paired records with 0 renames, 11/11 to valid in one round, and both regression cases correct on Python, Node and Bun. Investigate a drop against those shapes.

Record the result as a dated addendum on docs/project/reviews/review-2026-08-29-softschema-v080-readiness.md (append, never rewrite).
