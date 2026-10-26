---
type: is
id: is-01m5rxe8hwnpmcn6nzn13we921
title: "PR #59 C3: validate_values(schema=absent path) reports schema_invalid/compilation not schema_missing"
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
created_at: 2026-10-25T06:54:46.844Z
updated_at: 2026-10-25T07:16:46.612Z
started_at: 2026-10-25T06:54:52.907Z
closed_at: 2026-10-25T07:16:46.611Z
close_reason: "fixed in e02b064: FileNotFoundError -> schema_missing in validate_structural; test_values_schema_path_that_does_not_exist_is_schema_missing"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5641920187. validate.py validate_structural/_validator_for read_utf8 FileNotFoundError. Fix: report schema_missing; unit test.
