---
title: Enforced Closure for Composed Schemas
description: Close composed object schemas with unevaluatedProperties instead of refusing them
author: Claude Code, with maintainer direction from Joshua Levy
---
# Feature: Enforced Closure for Composed Schemas

**Date:** 2026-08-23 (last updated 2026-08-23)

**Author:** Claude Code, with maintainer direction from Joshua Levy

**Status:** Proposed.
Design validated against a working prototype; not implemented.

**Tracking:** GitHub issue [#41](https://github.com/jlevy/softschema/issues/41)

## Overview

Under `status: enforced`, a schema that composes constraints with `allOf`, `if`/`then`,
or `dependentSchemas` fails with `enforcement_unsupported` for every document, valid or
not. The reporter’s case is exact and reproduces on `main`.

The refusal is not gratuitous: closing a composed schema with `additionalProperties`
does change its meaning, and the
[minimal hardening plan](done/plan-2026-07-11-minimal-softschema-hardening.md) chose the
refusal deliberately over a rewrite that silently breaks valid documents.
The defect is that the refusal is *over-broad*. It covers shapes that JSON Schema
2020-12 can close correctly, using the keyword designed for precisely this problem:
`unevaluatedProperties`.

This plan replaces the refusal with an annotation-aware closure, splits applicators into
the two kinds that need different treatment, and absorbs the engine-parity work that
supporting these shapes newly exposes.

## Goals

- Validate conditional and composed schemas under `enforced` instead of refusing them,
  reporting the real violation rather than a generic message about `allOf`.
- Keep closure semantics-preserving: a document valid under `soft` and `permissive`
  stays valid under `enforced` unless it carries a genuinely undeclared property.
- Keep the `additionalProperties` closure, its compiled-schema neutrality, and the
  explicit-wins rule unchanged for schemas that do not compose.
- Normalize the Python/TypeScript error-record divergences that supporting these shapes
  makes reachable, and pin them with shared vectors and goldens.
- Make any residual refusal a schema-authoring diagnostic rather than a per-document
  `invalid` outcome.

## Non-Goals

- Changing compiled schemas.
  The overlay stays validation-time only.
- Closing object schemas that declare no properties anywhere (free-form mappings stay
  open, as today).
- Making every engine error set byte-identical across implementations.
  `anyOf` already diverges today (see Background); this plan does not widen that
  contract, it only covers the shapes it newly admits.
- Adding a cross-field validation vocabulary of softschema’s own.
  The point of the fix is that plain JSON Schema conditionals become usable.

## Background

### What the overlay does today

`apply_enforced_extras` walks the compiled schema and injects
`additionalProperties: false` into every object schema that declares `properties` and is
silent about `additionalProperties`. Before recursing, it refuses outright when an
`allOf` branch, a `dependentSchemas` value, or an `if`/`then`/`else`/`not` subschema
contains “open properties”:

```python
union = node.get("allOf")
if isinstance(union, list) and any(_contains_open_properties(branch) for branch in union):
    raise EnforcementUnsupportedError(
        "enforced closure is unsupported for allOf object composition"
    )
```

`validate_structural` turns that exception into a structural error record, so the
failure arrives per document, with `outcome: "invalid"`.

### Why the refusal exists

`additionalProperties` is *lexical*: it constrains only the properties named in the same
schema object, and is blind to properties contributed by sibling subschemas.
Closing a composed schema with it is genuinely wrong.
Confirmed against `jsonschema.Draft202012Validator`:

```yaml
type: object
properties: {a: {type: string}}
allOf:
  - properties: {b: {type: string}}
additionalProperties: false        # injected by the overlay
```

`{"a": "x", "b": "y"}` → `Additional properties are not allowed ('b' was unexpected)`.
The document satisfies the author’s schema and the overlay rejects it.
This is the exact shape of the shared `composed_object` vector in
`tests/vectors/hardening.yaml`, and the reason it is marked `supported: false`.

The `if` case is worse, because `if.properties` is a *matcher*, not a declaration.
Closing it changes which documents the rule fires on, so the conditional silently stops
firing rather than failing loudly.

So the original decision was sound.
What it missed is that 2020-12 has a keyword for closing composed objects, and
softschema’s own canonicalizer already recognizes it (`unevaluatedProperties` is in
`_SCHEMA_KEYWORDS`).

### The existing parity contract is narrower than it looks

Worth stating plainly, because it sets the bar for this work.
The two engines already disagree on error records for schemas the goldens do not
exercise. For `{"anyOf": [{"type": "string"}, {"type": "integer"}]}` against `{"x": 1}`:

| Engine | Records |
| --- | --- |
| Python `jsonschema` | one `anyOf` |
| ajv | two `type` plus one `anyOf` |

No golden covers it.
The parity invariant in [development.md](../../development.md) is upheld *for the
corpus*, not for arbitrary schemas.
The relevance here is direct: this fix widens the set of schemas that reach the
validator, which converts latent divergences into user-visible ones.
That conversion, not the closure rewrite, is the larger half of the work.

## Design

### The applicator split

The current code already distinguishes two groups, and the distinction is right — it is
just applied as “refuse” rather than “close differently”.

| Group | Keywords | Nature | Treatment |
| --- | --- | --- | --- |
| **Alternatives** | `anyOf`, `oneOf` | each branch describes the instance *completely* | close each branch, as today |
| **Fragments** | `allOf`, `if`, `then`, `else`, `not`, `dependentSchemas` | each subschema contributes *part* of one instance’s constraints | never close a fragment; close the composition root instead |

Closing an alternative branch is correct and already relied on:
`anyOf: [{object}, {"type": "null"}]` is the compiled shape of an optional model field,
and `test_recurses_into_anyof_branches` pins it.
Closing a fragment is what breaks.

### The closure rule

Replace the refusal with three clauses, evaluated at each schema node:

1. **Never inject closure inside a fragment subtree.** A fragment is a constraint
   contribution, not a payload declaration.
   `$defs` resets this: definitions are complete declarations reached by `$ref`, so they
   close on their own terms even when the reference sits inside a fragment.
2. **A node is a property-declaring object** if it declares `properties`, *or* if a
   fragment applicator under it declares properties.
   The second clause matters: the `composed_object` vector declares all its properties
   inside `allOf` branches, and without it that schema would be enforced nowhere.
3. **Close a property-declaring object** that sets neither `additionalProperties` nor
   `unevaluatedProperties` — with `unevaluatedProperties: false` when it carries a
   fragment applicator, and `additionalProperties: false` otherwise.
   Explicit values keep winning, and free-form mappings stay untouched.

`unevaluatedProperties` is annotation-aware: properties evaluated by `properties`, by
`allOf` branches, by a successful `if`, by `then`/`else`, by `dependentSchemas`, and
through `$ref` all count as evaluated.
Only genuinely undeclared keys fail.

### Verification

Prototyped in `canonicalize.py` and run against both engines.
The reporter’s schema, and the shared vector the refusal was built for:

| Case | Today | With the rule |
| --- | --- | --- |
| (a) valid document, `enforced` | `invalid` — `enforcement_unsupported` | `valid`, exit 0 |
| (b) `kind: special` without `extra` | `invalid` — `enforcement_unsupported` | `invalid` — `required property ['extra'] is missing` |
| (c) undeclared key `bogus` | `invalid` — `enforcement_unsupported` | `invalid` — closure violation |
| `composed_object` vector, `{first, last}` | refused | valid |
| `composed_object` vector, `{first, last, bogus}` | refused | rejected on `bogus` |

Case (b) is the one the issue calls out, and it now reports the actionable error.

Regression surface, with the prototype in place: **174 of 176 Python tests pass, and the
full golden corpus passes (44 scenarios).** The two failures are exactly the tests that
pin the old refusal — `test_shared_enforcement_vectors` and
`test_structural_validation_reports_unsupported_enforcement` — both of which this plan
rewrites.

### `enforcement_unsupported` becomes unreachable

Under the rule there is no shape the overlay must refuse: fragments are left alone and
roots close annotation-aware.
`EnforcementUnsupportedError` is never raised, and `_contains_open_properties` becomes
dead code. See Open Questions for whether to retire the error kind or reserve it.

This also answers the issue’s fallback request ("raise when the schema is loaded"). It
is worth recording why that fallback is the *weaker* option, not just the unchosen one:
`enforcement_unsupported` and `schema_invalid` both classify as `outcome: "invalid"`
today, because `input_codes` in `ArtifactValidationResult.__post_init__` is limited to
`artifact_unreadable` and `artifact_invalid_utf8`. Moving schema-authoring failures to
their own outcome would change exit classes for `schema_invalid` too — a breaking change
to the result contract, for a code path this design removes.

### Parity work this newly exposes

Supporting these shapes makes three divergences reachable.
All three are measured, not predicted.

**1. Closure-error multiplicity.** For `{first, last, bogus, other}`:

| Engine | Records |
| --- | --- |
| Python | one `unevaluatedProperties` naming both keys |
| ajv | one `unevaluatedProperties` *per key* |

Identical in shape to the `additionalProperties` divergence that
`collapseAdditionalProperties` already solves, and identical in remedy: softschema
records carry no key names, so post-normalization records for one path are
byte-identical and keeping the first reproduces Python’s shape.
Generalize the helper to both keywords.

**2. Missing message template.** Neither `errors.py` nor `errors.ts` has a
`unevaluatedProperties` case, so violations fall to the generic branch:

```
value {'kind': 'plain', 'bogus': 1} failed unevaluatedProperties constraint False
```

That is unhelpful, and it spills the whole payload into the message — worse than the
`additionalProperties` wording it should mirror.
Add the template to both.

**3. ajv’s `if` wrapper.** For the reporter’s case (b):

| Engine | Records |
| --- | --- |
| Python | `required` |
| ajv | `required`, plus `if` — `must match "then" schema` |

The `if` record restates the inner cause.
Python never emits one (a failing `if` is not an error, it is a false condition), so
suppressing `if` records in normalization aligns ajv to Python without losing
information.

**4. `dependentSchemas`, a real residual.** When a dependent schema fails, ajv adds an
`unevaluatedProperties` record naming a property that top-level `properties` already
evaluated:

```
required            #/dependentSchemas/a/required   missingProperty: b
unevaluatedProperties  #/unevaluatedProperties       unevaluatedProperty: a
```

Python reports only `required`. Both engines agree the document is **invalid**; they
disagree on the record set, and no normalization removes it cleanly.
This sits in the same class as the pre-existing `anyOf` divergence.
Resolved by maintainer direction: support the shape.
Functionally equivalent, language-native error differences are acceptable when tests
document them — Python goldens are the reference output, and accepted TypeScript
deviations are checked in and validated (see Testing Strategy).

## Implementation Plan

Follows the golden-first parity process in [development.md](../../development.md):
failing vector first, then Python, then the TypeScript port, then both golden runs.

### Phase 1: Characterize

- Add the reporter’s schema and documents to `tests/golden/fixtures/` as a conditional
  artifact, with scenarios for the valid, rule-violating, and undeclared-key cases.
- Extend `tests/vectors/hardening.yaml`: flip `composed_object` to `supported: true`,
  and add vectors for a bare top-level `if`/`then`, a fragment declaring properties the
  root does not, and a `$ref` from inside a fragment.
- Give each supported vector an expected closure keyword so both runtimes assert *which*
  keyword the overlay injects, not merely that closure happened.

### Phase 2: Python

- Rewrite `_apply_enforced_extras` to the three clauses, threading an `in_fragment` flag
  and resetting it under `$defs`.
- Delete `_contains_open_properties`, and resolve `EnforcementUnsupportedError` per the
  Open Questions decision.
- Add the `unevaluatedProperties` message template to `errors.py`.
- Update `apply_enforced_extras`’s docstring: it is the reference prose for the rule.

### Phase 3: TypeScript

- Mirror the closure rule in `canonicalize.ts`.
- Generalize `collapseAdditionalProperties` to both closure keywords, renaming it for
  what it now does.
- Suppress ajv `if` wrapper records in `normalizeAjvError`’s caller.
- Add the matching template to `errors.ts`.

### Phase 4: Documentation

- `docs/softschema-spec.md`, Status Values: the closure is no longer a single-keyword
  rule. State the applicator split, both keywords, and that fragments are never closed.
- `docs/softschema-guide.md` line 262: extend the parenthetical so the Step 5
  description stays true for composed schemas.
- Add a short “cross-field rules” example to the guide — the issue’s
  `decision: abandoned` requires `budget_spent` shape is the natural one, and its
  absence is part of why the limitation went unnoticed.
- CHANGELOG entry under a fix heading, noting that schemas previously refused now
  validate.
- `docs/development.md`: record the deviation policy — cross-implementation output is
  identical except for deviations explicitly checked in as documented diffs, with the
  Python goldens as the reference.

## Testing Strategy

| Concern | Where |
| --- | --- |
| Closure rule per shape | shared `hardening.yaml` enforcement vectors, run by both runtimes |
| Which keyword is injected | expected-keyword field on each supported vector |
| Fragments left open | unit assertion that no closure key appears under `if`/`allOf` branches |
| Explicit-wins, free-form untouched | existing `test_enforced_extras.py` cases, unchanged |
| Alternatives still closed | `test_recurses_into_anyof_branches`, unchanged |
| Real violation surfaces | golden scenario on the reporter’s case (b) |
| Engine-neutral records | golden corpus run twice via `SOFTSCHEMA_IMPL`, plus `cross-impl-diff.sh` |
| Known engine deviations | checked-in documented diffs against the Python golden reference, validated by `cross-impl-diff.sh` — covering the `dependentSchemas` record set and the pre-existing `anyOf` multiplicity, so an unlisted divergence still fails |

Both refusal-pinning tests are rewritten rather than deleted: they become the assertions
that these shapes are now *supported*, which keeps the regression visible if the rule
ever narrows again.

## Compatibility

- **Schemas previously refused now validate.** Documents that were uniformly `invalid`
  become `valid` or report a real violation.
  Strictly an improvement, but it moves exit codes for anyone who pinned the broken
  behavior; it belongs in a minor release with a changelog note.
- **A composed schema gains real enforcement.** A document with an undeclared key
  against a composed schema was `invalid` before (for the wrong reason) and is `invalid`
  after (for the right one).
  No document silently becomes valid.
- **Non-composed schemas are bit-identical.** Clause 3 keeps `additionalProperties` for
  them, which is why the golden corpus passes untouched.
- **Compiled schemas and `schema_sha256` are unaffected.** The overlay remains
  validation-time only.
- One behavioral widening deserves a maintainer’s eye: `unevaluatedProperties` is
  annotation-based, so a property named in an `if` matcher is *evaluated* when the
  matcher succeeds, and is therefore admitted.
  Given `if: {properties: {secret: {const: "x"}}}` with no `secret` in the root’s
  `properties`, `{"secret": "x"}` passes closure while `{"secret": "other"}` is
  rejected. This is correct 2020-12 behavior, it is narrow, and it is the price of
  annotation-aware closure — but it should be documented in the spec rather than
  discovered.

## Decision Summary

| Decision | Rationale |
| --- | --- |
| Close with `unevaluatedProperties`, do not traverse `allOf` with `additionalProperties` | The issue’s first suggestion, read literally, reintroduces the bug the refusal guards. Verified against both engines. |
| Split applicators into alternatives and fragments | The existing code already draws this line; only its consequence changes. |
| Treat a fragment-declaring node as property-declaring | Otherwise the `composed_object` vector is enforced nowhere. |
| Never close inside a fragment | Closing an `if` matcher silently stops a conditional from firing — the worst failure mode available. |
| Keep the diagnostic at validation time | The refusal disappears; relocating it would require changing `schema_invalid`’s outcome class too. |
| Support `dependentSchemas`, pinning engine deviations as documented diffs | Maintainer direction: functionally equivalent, language-native differences are fine when tests record them; Python goldens are the reference. |

## Open Questions

1. **Retire `enforcement_unsupported`?** It becomes unreachable, and it has no official
   surface to preserve: the string appears in no spec, guide, README, or changelog
   entry, and `EnforcementUnsupportedError` is exported by neither package (absent from
   the Python `__all__` and the TypeScript `index.ts`). Keeping it
   defined-but-never-emitted would protect nobody — an output string is not a symbol, so
   a consumer matching on it loses that branch the moment emission stops, whether or not
   a constant remains in source.
   Recommend: delete the kind, the exception class, and the vector `code` field; the
   changelog entry is the notice.
2. **Report `unevaluatedProperties` as the `validator`, or normalize?** The same logical
   violation — an undeclared key — now reports `additionalProperties` for a simple
   schema and `unevaluatedProperties` for a composed one, so a consumer matching the
   former misses composed cases.
   Reporting the true keyword matches the documented record shape (`validator` is “the
   JSON Schema keyword”); normalizing is kinder to consumers.
   Recommend: report truthfully, and call out the pair in the spec.
3. **Is `unevaluatedProperties`’s evaluation cost worth measuring?** It defeats some ajv
   optimizations. It applies only to composed schemas under `enforced`, so the blast
   radius is small, but the memoization added in 0.6.2 makes a before/after worth a
   glance.

## References

- GitHub issue [#41](https://github.com/jlevy/softschema/issues/41)
- [Minimal Softschema Hardening](done/plan-2026-07-11-minimal-softschema-hardening.md),
  which introduced the refusal
- [softschema Spec](../../softschema-spec.md), Status Values
- [JSON Schema 2020-12 Core](https://json-schema.org/draft/2020-12/json-schema-core.html),
  `unevaluatedProperties` and annotation collection
- [ajv unevaluatedProperties](https://ajv.js.org/json-schema.html#unevaluatedproperties)
- tbd `common-doc-guidelines`
- tbd `golden-testing-guidelines`

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
