---
type: is
id: is-01m5svsabrdgn42ec1k2bzr06w
title: "PR #59 leftovers: refuse non-string $schema in Python; align malformed-URN $ref reason"
kind: task
status: closed
priority: 2
version: 2
labels: []
dependencies: []
created_at: 2026-10-25T15:45:06.424Z
updated_at: 2026-10-25T15:52:30.508Z
closed_at: 2026-10-25T15:52:30.508Z
close_reason: "Fixed in 206cd9d (pushed to enforcement-clarity). (1) Python _check_dialect checks $schema type before the frozenset lookup; vectors array/mapping/nested-mapping/null/boolean-schema-keyword; array-schema-keyword failed before (compilation, unhashable list) and passes after. (2) TS buildValidator reclassifies fast-uri 'URN without nid cannot be serialized' as reference when a $ref value itself fails to serialize; vector malformed-urn-reference failed in TS before, passes after. pytest 272, lint pass, bun test 398, typecheck/lint:ci/build clean, goldens py 87 / ts 85, cross-impl OK; CI 40208739603 17/18 (typescript audit only, #64). Qodo reply https://github.com/jlevy/softschema/pull/59#discussion_r4371414531 (thread resolved); addendum https://github.com/jlevy/softschema/pull/59#issuecomment-6399779629"
resolution: null
duplicate_of: null
---
Coordinator follow-up after review F on https://github.com/jlevy/softschema/pull/59. (1) Qodo inline https://github.com/jlevy/softschema/pull/59#discussion_r4370066190 (Medium, packages/python/src/softschema/validate.py:544): _check_dialect hashes $schema before checking its type, so [] / {} give reason compilation in Python vs dialect in TypeScript. (2) A dangling $ref to a URN with no namespace identifier (urn:dir/item.json) is not_run in both but reason reference in Python vs compilation in TypeScript (fast-uri 'URN without nid cannot be serialized').
