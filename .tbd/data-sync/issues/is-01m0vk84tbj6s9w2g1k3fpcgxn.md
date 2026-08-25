---
type: is
id: is-01m0vk84tbj6s9w2g1k3fpcgxn
title: Accept nullable references to explicitly closed generated models
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01m0tenataem0p1w6xmrynypvt
created_at: 2026-08-25T04:35:54.826Z
updated_at: 2026-08-25T04:48:42.539Z
closed_at: 2026-08-25T04:48:42.538Z
close_reason: Pure reference chains to explicitly closed targets no longer receive redundant inferred closure. Added shared nullable generated-model vector; 1,547 GTIA tests and both runtime suites pass.
resolution: null
duplicate_of: null
---
PR #44 returned composition_reference_context for the common Pydantic-generated anyOf [$ref, null] shape even when referenced object graphs were explicitly closed. This broke valid GTIA FollowOnQueryContext and CohortReviewBundle artifacts. Avoid redundant inferred closure at pure references to explicitly closed targets, with parity tests in Python and TypeScript and downstream verification.
