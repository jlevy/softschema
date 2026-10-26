---
type: is
id: is-01m5rxe6kxdphbp2nsp0rvxw8j
title: "PR #59 B5: Ajv evaluates legacy dependencies keyword, jsonschema ignores it"
kind: bug
status: closed
priority: 3
version: 4
spec_path: docs/project/specs/done/plan-2026-09-12-validation-execution-evidence.md
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rxe40c2nyv4rwytvha8dhy
hold: null
hold_until: null
created_at: 2026-10-25T06:54:44.861Z
updated_at: 2026-10-26T03:34:07.490Z
started_at: 2026-10-25T06:54:51.718Z
closed_at: 2026-10-25T07:16:44.673Z
close_reason: "fixed in e02b064: both runtimes refuse legacy dependencies as schema_invalid/dialect; vector legacy-dependencies-keyword; CHANGELOG/spec"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5641896780. Pre-existing. Fix: refuse dependencies as schema_invalid/dialect in both, strip, or pin.
