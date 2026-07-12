---
type: is
id: is-01kxa153asfr235gahrg2124h0
title: "PR #21 review R1: map Python input errors to exit 2"
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01kxa14h09j4qnzmmj02pv5jzt
created_at: 2026-07-12T02:05:29.816Z
updated_at: 2026-07-12T02:08:11.874Z
closed_at: 2026-07-12T02:08:11.874Z
close_reason: "Fixed in the PR #21 review follow-up with focused red/green regression coverage."
---
PR #21 Bugbot medium finding at packages/python/src/softschema/cli.py:315: _validate_cmd returns 1 for all failed ArtifactValidationResult values instead of deriving exit 0/1/2 from outcome.
