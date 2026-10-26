---
type: is
id: is-01m5t19n7rfx7v6c9dstqej00c
title: "PR #66 A1: zod 4.6 lists .catch() fields in required, breaking Pydantic parity (Medium; compile.ts override, CHANGELOG.md:95-97, lib-units.test.ts:537-538; https://github.com/jlevy/softschema/pull/66#pullrequestreview-5644323058)"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5t19mwqkqn05e0232pa182s
hold: null
hold_until: null
created_at: 2026-10-25T17:21:24.728Z
updated_at: 2026-10-25T17:35:38.886Z
started_at: 2026-10-25T17:21:33.001Z
closed_at: 2026-10-25T17:35:38.886Z
close_reason: "fixed: .catch() fields removed from required (also behind z.preprocess and in $defs); digest fafbf480 = Pydantic f: str = 'x' = zod 4.4.3; unit test 'compiles a .catch() field as the defaulted field...' fails with the fix off. PR #66 commit f22ff4463ce788aa530fe5318caa3f903de7ea21 (merged with main in 03425e3); CI run 40216906758 19/19 pass; dispositions https://github.com/jlevy/softschema/pull/66#issuecomment-6400894968"
resolution: null
duplicate_of: null
---
