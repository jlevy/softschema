---
type: is
id: is-01m0pkvkvwwm4xfn5pnvyyaqnq
title: "Enforced closure and anyOf/oneOf: over-rejection beside siblings, under-enforcement inside fragments"
kind: bug
status: open
priority: 1
version: 2
labels:
  - enforcement
  - json-schema
dependencies: []
created_at: 2026-08-23T06:10:20.668Z
updated_at: 2026-08-23T09:14:49.209Z
---
Two related defects in how the enforced overlay treats anyOf/oneOf. Both need the SAME maintainer decision about branch-closure semantics, so they are tracked together.

--- Fault A: over-rejection when alternatives sit beside sibling properties (original report) ---

When a node declares its own `properties` AND carries an anyOf/oneOf whose branches declare more, both the root and every branch get closed lexically, and a document valid under the raw schema is rejected.

  schema = {type: object, properties: {a: {type: string}},
            anyOf: [{properties: {b: {type: string}}},
                    {properties: {c: {type: string}}}]}
  doc    = {a: "x", b: "y"}    valid under the raw schema, invalid under enforced

Root closure is now fixable the way PR #42 fixed fragments (unevaluatedProperties). Branch closure is the open question: each branch's additionalProperties cannot see `a`, contributed by the root, so every branch fails and the anyOf fails with it. Suppressing branch closure when the node has sibling `properties` is the obvious candidate but narrows enforcement.

--- Fault B: under-enforcement when alternatives are nested inside a fragment (PR #42 review, R4) ---

  schema = {allOf: [{anyOf: [{properties: {a}}, {properties: {b}}]}]}
  doc    = {a: "x", zzz: 1}    zzz undeclared, accepted under enforced

Nothing closes anywhere: branches inherit fragment status (correctly — closing them would be lexically blind to siblings), and the declares-scan does not traverse alternatives, so the root does not close either. Wrapping an anyOf in allOf is a no-op refactor in raw JSON Schema that silently turns enforcement off, while the identical top-level anyOf rejects undeclared keys via branch closure.

Opposite direction from Fault A, same root cause: closure is decided lexically per schema object, but whether an alternative branch is a complete declaration depends on how it is reached. Closing the root over hoisted branch declarations would give union semantics that differ from top-level branch closure — that is the decision needed.

Current behavior for Fault B is pinned as the `alternatives_inside_fragment` entry in the `enforcement_gaps` vectors and documented under "What enforced does not close" in the spec, so it is visible rather than silent. Fault A ships unpinned.
