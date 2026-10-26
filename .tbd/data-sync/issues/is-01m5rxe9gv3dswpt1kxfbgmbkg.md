---
type: is
id: is-01m5rxe9gv3dswpt1kxfbgmbkg
title: "PR #59 Qodo 1: TS --require payload usage error lacks softschema validate: prefix"
kind: bug
status: closed
priority: 3
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rxe40c2nyv4rwytvha8dhy
hold: null
hold_until: null
created_at: 2026-10-25T06:54:47.835Z
updated_at: 2026-10-25T07:16:47.596Z
started_at: 2026-10-25T06:54:53.645Z
closed_at: 2026-10-25T07:16:47.596Z
close_reason: "fixed in 1289d8a: --require values judged in runValidate via UsageError -> softschema validate: invalid require: ...; golden asserts prefix in both CLIs"
resolution: null
duplicate_of: null
---
Low (Qodo says High). https://github.com/jlevy/softschema/pull/59#discussion_r4369879124. packages/typescript/src/cli.ts:552-553. Fix if small (route like --status), else decline citing cli-errors.tryscript.md:73-82.
