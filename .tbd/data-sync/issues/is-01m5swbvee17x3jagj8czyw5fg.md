---
type: is
id: is-01m5swbvee17x3jagj8czyw5fg
title: "PR #59: refuse urn: $id without a namespace identifier in both runtimes"
kind: task
status: closed
priority: 2
version: 3
delegate: claude-code@vm
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-25T15:55:13.742Z
updated_at: 2026-10-25T16:06:55.626Z
started_at: 2026-10-25T15:55:14.858Z
closed_at: 2026-10-25T16:06:55.626Z
close_reason: "Fixed in d9b9e6f (pushed to enforcement-clarity). Both runtimes refuse a urn: $id (root/nested, root schema or supplied resource) and a urn: resource key (resource without $id) lacking a namespace identifier as schema_invalid/resource_identity before engine compilation, raw and enforced; rule mirrors fast-uri URN_REG over ASCII. Vectors in validation-execution.yaml (refuse: root urn:example raw+enforced, root urn:dir/item.json, nested urn:example; accept: urn:uuid raw+enforced, nested urn:isbn, URN:Example:Root) and hardening.yaml (resource $id/key refuse, namespaced key accept). Spec, python design doc, CHANGELOG updated. F1 pin kept (not moot). pytest 272, lint pass, bun test 414, typecheck/lint:ci/build clean, goldens py 87 / ts 85, cross-impl OK; CI 40209896505 17/18 (typescript audit only, #64). Addendum https://github.com/jlevy/softschema/pull/59#issuecomment-6399934514"
resolution: null
duplicate_of: null
---
Coordinator decision after review F on https://github.com/jlevy/softschema/pull/59: a $id (root or nested, raw and enforced) that is a urn: with no valid namespace identifier (fast-uri URN_REG) gave Python completed vs TypeScript not_run/compilation ('URN without nid cannot be serialized'). Refuse it in both runtimes as schema_invalid/resource_identity before compilation; vectors, spec resource-identity rule, CHANGELOG Compatibility line.
