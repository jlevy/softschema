---
type: is
id: is-01m5rxe820kmkks5fg1sfa0z0n
title: "PR #59 C2: pre-existing engine differences exposed by execution are unpinned (cycles, root $dynamicRef reason, $ref to non-schema, draft-07 $schema, $id+$ref siblings)"
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
created_at: 2026-10-25T06:54:46.335Z
updated_at: 2026-10-25T07:16:46.143Z
started_at: 2026-10-25T06:54:52.491Z
closed_at: 2026-10-25T07:16:46.142Z
close_reason: "fixed in e02b064 + 11f2d34: draft-07 $schema refused in both (dialect); root self-ref agrees (ordinary vector); reference-cycle, root-dynamic-reference, reference-to-non-schema-location, id-and-ref-siblings, embedded-id-with-resolvable-ref-sibling pinned as engine_deviations; spec lists them"
resolution: null
duplicate_of: null
---
Low. https://github.com/jlevy/softschema/pull/59#pullrequestreview-5641920187. Fix: engine_deviations vectors + spec section, or small parity fixes where safe.
