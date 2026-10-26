---
type: is
id: is-01m5sv7hm0xzh400kjb1vvgepn
title: "PR #59 review F: pin urn nested-id deviation; name unevaluatedProperties mechanism"
kind: task
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-25T15:35:24.031Z
updated_at: 2026-10-25T15:40:51.316Z
started_at: 2026-10-25T15:35:29.529Z
closed_at: 2026-10-25T15:40:51.315Z
close_reason: "Review F fixed in 0ed64b8 (pushed to enforcement-clarity). F1: pinned urn-root-nested-relative-id and tag-root-nested-relative-id-absolute-reference in tests/vectors/validation-execution.yaml engine_deviations; spec list names a relative $id under a non-hierarchical root such as urn: or tag:. F2: why names jsonschema descending every instance value into unevaluatedProperties; added unevaluated-properties-beside-closed-additional-properties-reached. Evidence: pytest 272 passed, lint pass, bun test 386 pass, typecheck/lint:ci/build clean, goldens py 87 / ts 85, cross-impl parity OK; CI run 40207900117 17/18 (typescript fails only at Audit dependencies, #64). Reply: https://github.com/jlevy/softschema/pull/59#issuecomment-6399654504"
resolution: null
duplicate_of: null
---
Review F (follow-up, round 4, approve) on https://github.com/jlevy/softschema/pull/59#pullrequestreview-5642158866. F1 (Low): urn: root $id with nested relative $id is an unlisted engine difference; pin in tests/vectors/validation-execution.yaml engine_deviations and list in docs/softschema-spec.md. F2 (Low): name jsonschema's find_evaluated_property_keys_by_schema mechanism in the unevaluated-properties-beside-additional-properties-reached why (tests/vectors/validation-execution.yaml:569-580) and add the additionalProperties: false variant.
