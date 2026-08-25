---
type: is
id: is-01m0vk84h0dvy7640g1t5abf5k
title: Preserve model-only enforced contract compatibility
kind: bug
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01m0tenataem0p1w6xmrynypvt
created_at: 2026-08-25T04:35:54.527Z
updated_at: 2026-08-25T04:48:42.287Z
closed_at: 2026-08-25T04:48:42.286Z
close_reason: Restored 0.6.2 model-only and metadata-only verdicts and skip reasons in Python and TypeScript; documented native semantic delegation; 4,270 metaproc tests and all softschema checks pass.
resolution: null
duplicate_of: null
---
PR #44 changes existing model-only contracts with status enforced from semantic validation plus a skipped structural pass to enforced_schema_required. This breaks live metaproc registry contracts and six targeted downstream tests under the existing softschema>=0.6,<0.7 dependency range. Preserve the released behavior for existing calls in both runtimes, keep added status/resources options additive, update tests/docs/changelog, and verify downstream.
