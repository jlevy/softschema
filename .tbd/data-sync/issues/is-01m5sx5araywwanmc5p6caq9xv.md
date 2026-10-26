---
type: is
id: is-01m5sx5araywwanmc5p6caq9xv
title: "PR #59: compile --schema-id refuses ids validation refuses as resource_identity"
kind: task
status: closed
priority: 2
version: 2
labels: []
dependencies: []
created_at: 2026-10-25T16:09:08.617Z
updated_at: 2026-10-25T16:17:16.344Z
closed_at: 2026-10-25T16:17:16.344Z
close_reason: "Fixed in 4112fab (pushed to enforcement-clarity). compile --schema-id / schema_id / schemaId now calls the shared root-identity helper (_check_root_id / checkRootId) that validation uses: relative ids and urn: ids without a namespace identifier are refused as SchemaGraphError resource_identity (ValueError / plain Error, CLI exit 2), byte-identical messages (Python quotes as JSON). Unit test per runtime (test_compile_refuses_a_schema_id_that_validation_refuses; 'a schemaId that validation refuses is refused at compile time'), golden blocks in scenarios-py and scenarios-ts-bun compile.tryscript.md. pytest 273, lint pass, bun test 415, typecheck/lint:ci/build clean, goldens py 89 / ts 85 / ts-bun 89, cross-impl OK; CI 40210725946 17/18 (typescript audit only, #64). Addendum https://github.com/jlevy/softschema/pull/59#issuecomment-6400047544"
resolution: null
duplicate_of: null
---
Coordinator follow-up on https://github.com/jlevy/softschema/pull/59: softschema compile --schema-id (packages/python/src/softschema/compile.py:47, packages/typescript/src/compile.ts:114) only checks the id is absolute, so it can write a urn: root $id without a namespace identifier that validation now refuses. Share one root-identity helper per runtime between validate and compile; same message wording and exit class (2) in both; tests per runtime.
