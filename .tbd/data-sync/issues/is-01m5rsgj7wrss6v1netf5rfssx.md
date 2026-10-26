---
type: is
id: is-01m5rsgj7wrss6v1netf5rfssx
title: "PR #59 A1: --require structural passes in Python, fails in TypeScript for unreached $ref in raw mode"
kind: bug
status: closed
priority: 2
version: 4
spec_path: docs/project/specs/done/plan-2026-09-12-validation-execution-evidence.md
delegate: claude-code@vm
labels: []
dependencies: []
parent_id: is-01m5rr5w4r03h667rqqwvz0a5s
hold: null
hold_until: null
created_at: 2026-10-25T05:46:07.996Z
updated_at: 2026-10-26T03:34:06.199Z
started_at: 2026-10-25T05:46:16.573Z
closed_at: 2026-10-25T06:13:11.174Z
close_reason: "fixed in b058d1c: Python preparation resolves every reachable $ref (_check_references) so an unresolvable local or remote reference is schema_invalid/reference with not_run in both runtimes; vectors unreached-local-reference, unreached-remote-reference, unreached-reference-required-structural, unreferenced-definition-dangling-reference in tests/vectors/validation-execution.yaml (fail before, pass after); spec, python design, plan, CHANGELOG updated"
resolution: null
duplicate_of: null
---
Severity: Medium. PR #59. Review A: https://github.com/jlevy/softschema/pull/59#pullrequestreview-5641723707. Refs: packages/python/src/softschema/validate.py:276-279 (lazy ref resolution), packages/typescript/src/validate.ts:340-347 (Ajv resolves eagerly), docs/softschema-spec.md:788-793, tests/vectors/validation-execution.yaml:87-97. Coordinator decision: real parity fix, Python resolves every $ref during preparation (golden-first per docs/development.md); no network fetching.
