---
type: is
id: is-01m5tbxy60pawvc845dn8nkaj1
title: "Zod drops the default of .transform().default() in input JSON Schema (zod 4.4 and 4.6); Pydantic Annotated[str, AfterValidator(f)] = 'x' keeps default (fafbf480 vs 764f02a3). Pre-existing parity gap found while fixing PR #66 B1; decide whether to restore it like the catch value."
kind: bug
status: closed
priority: 3
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-25T20:27:15.008Z
updated_at: 2026-10-25T21:35:50.490Z
started_at: 2026-10-25T20:49:03.037Z
closed_at: 2026-10-25T21:35:50.489Z
close_reason: "Fixed in PR #67 (https://github.com/jlevy/softschema/pull/67), head 3e11152, CI 19/19 green. compile.ts override restores a .default() value Zod drops over a transform (same path as the #66 catch value, through jsonDefault); a $ref node settles against its $defs entry as Zod's dedup does. Digests (x:Repro/v1, f: ...): transform.default 02dfd38b -> f31c2ad4 = Pydantic Annotated[str, AfterValidator(f)] = 'x'; record value c9e5c83d -> 6bf89142 = Pydantic; $defs object default 48ad7e58 -> f6392cec = Pydantic. KitchenSink gains slug (transform+default): 6fafec02 -> 6810f0d8, identical from Python and TS compile --check. Unit tests in lib-units.test.ts fail with the fix disabled."
resolution: null
duplicate_of: null
---
