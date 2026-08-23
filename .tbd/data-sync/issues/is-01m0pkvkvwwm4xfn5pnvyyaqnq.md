---
type: is
id: is-01m0pkvkvwwm4xfn5pnvyyaqnq
title: Enforced closure is lexically blind to anyOf/oneOf branches that declare properties
kind: bug
status: open
priority: 1
version: 1
labels:
  - enforcement
  - json-schema
dependencies: []
created_at: 2026-08-23T06:10:20.668Z
updated_at: 2026-08-23T06:10:20.668Z
---
Sibling of issue #41, but with ALTERNATIVES instead of fragments, and the enforcement_unsupported refusal never covered it — so it ships today, silently, and the closure spec (ss-r9u8) does not address it.

When a node declares its own `properties` AND carries an `anyOf`/`oneOf` whose branches declare further properties, the overlay injects `additionalProperties: false` at the root and into every branch. Both injections are lexically blind, so a document valid under the raw schema is rejected under `enforced`.

Reproduced against apply_enforced_extras on main:

  schema = {type: object, properties: {a: {type: string}},
            anyOf: [{properties: {b: {type: string}}},
                    {properties: {c: {type: string}}}]}
  doc    = {a: "x", b: "y"}

  valid under the raw schema:  True
  under the enforced overlay:  errors [anyOf, additionalProperties]

Two distinct faults in one shape:
1. Root `additionalProperties: false` cannot see `b`, contributed by the anyOf branch.
2. Branch `additionalProperties: false` cannot see `a`, contributed by the root — so EVERY branch fails and the anyOf fails with it.

Fault 2 is the interesting one: the closure spec's applicator split justifies closing alternative branches on the grounds that each branch 'describes the instance completely'. That holds for the compiled optional-field shape (anyOf: [{$ref}, {type: null}] — no sibling properties) which is what test_recurses_into_anyof_branches pins, but not when the root declares properties alongside.

Root closure is fixable the same way ss-r9u8 fixes fragments: `unevaluatedProperties: false` admits {a, b} correctly (verified). Branch closure is the open design question — suppressing it when the node has sibling `properties` is the obvious candidate, but it narrows enforcement for that shape and wants a maintainer call.

Deliberately left out of ss-r9u8's scope: that epic is scoped to fragments and issue #41, and this needs a decision rather than a port. Pick it up after the closure rule lands, when unevaluatedProperties is already wired through both engines.
