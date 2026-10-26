---
type: is
id: is-01m5t19njdmgq4y8m5ha5xffcp
title: "PR #66 A2: zero-length tuples differ from Pydantic tuple[()] and tuple[int, ...] (Low; compile.ts:143-152, CHANGELOG.md:78-81, softschema-spec.md:637; https://github.com/jlevy/softschema/pull/66#pullrequestreview-5644323058)"
kind: bug
status: closed
priority: 2
version: 2
labels: []
dependencies: []
parent_id: is-01m5t19mwqkqn05e0232pa182s
created_at: 2026-10-25T17:21:25.069Z
updated_at: 2026-10-25T17:35:39.262Z
closed_at: 2026-10-25T17:35:39.262Z
close_reason: "fixed: empty prefixItems dropped, z.tuple([]) gets minItems 0 (= tuple[()] ec1f21a4), empty rest tuple = tuple[int, ...] (674349e7); pinned in unit test. PR #66 commit f22ff4463ce788aa530fe5318caa3f903de7ea21 (merged with main in 03425e3); CI run 40216906758 19/19 pass; dispositions https://github.com/jlevy/softschema/pull/66#issuecomment-6400894968"
resolution: null
duplicate_of: null
---
