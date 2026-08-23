---
title: Enforced Closure for Composed Schemas
description: Close composed object schemas with unevaluatedProperties instead of refusing them
author: Claude Code, with maintainer direction from Joshua Levy
---
# Feature: Enforced Closure for Composed Schemas

**Date:** 2026-08-23 (last updated 2026-08-23)

**Author:** Claude Code, with maintainer direction from Joshua Levy

**Status:** Implemented, pending release.
All four phases landed; the spec moves to `done/` when the release ships.

**Tracking:** `ss-r9u8` (enforced-closure epic), from GitHub issue
[#41](https://github.com/jlevy/softschema/issues/41)

## Overview

Under `status: enforced`, a schema that composes constraints with `allOf`, `if`/`then`,
or `dependentSchemas` fails with `enforcement_unsupported` for every document, valid or
not. The reporter’s case is exact and reproduces on `main`.

The refusal is not gratuitous: closing a composed schema with `additionalProperties`
does change its meaning, and the
[minimal hardening plan](../done/plan-2026-07-11-minimal-softschema-hardening.md) chose
the refusal deliberately over a rewrite that silently breaks valid documents.
The defect is that the refusal is *over-broad*. It covers shapes that JSON Schema
2020-12 can close correctly, using the keyword designed for precisely this problem:
`unevaluatedProperties`.

This plan replaces the refusal with an annotation-aware closure, splits applicators into
the two kinds that need different treatment, and absorbs the engine-parity work that
supporting these shapes newly exposes.
Because the closure now picks between two keywords, it also gives structural error
records a stable `code` enum, so consumers match a category rather than a keyword.

## Goals

- Validate conditional and composed schemas under `enforced` instead of refusing them,
  reporting the real violation rather than a generic message about `allOf`.
- Keep closure semantics-preserving: a document valid under `soft` and `permissive`
  stays valid under `enforced` unless it carries a genuinely undeclared property.
- Keep the `additionalProperties` closure, its compiled-schema neutrality, and the
  explicit-wins rule unchanged for schemas that do not compose.
- Normalize the Python/TypeScript error-record divergences that supporting these shapes
  makes reachable, and pin them with shared vectors and goldens.
- Give structural error records a stable `code` enum, so a consumer matches a
  softschema-owned category rather than whichever JSON Schema keyword the closure
  happened to use.
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
The parity invariant in [development.md](../../../development.md) is upheld *for the
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

### The `code` enum on structural error records

The closure rule splits one authoring mistake across two keywords: an undeclared key
reports `additionalProperties` on a simple schema and `unevaluatedProperties` on a
composed one. A consumer matching `validator == "additionalProperties"` therefore stops
seeing exactly the cases this plan newly admits.
Reporting the true keyword is right — `validator` is documented as the JSON Schema
keyword, and hiding which one fired would cost real diagnostic information — but it
cannot be the match surface.

By maintainer direction, structural error records gain a small closed `code` enum
alongside `validator`. `validator` names the *mechanism*; `code` names *what the author
got wrong*:

| `code` | Emitted for | Meaning |
| --- | --- | --- |
| `undeclared_property` | `additionalProperties`, `unevaluatedProperties` | a key the schema does not declare |
| `missing_property` | `required` | a declared key the document omits |
| `invalid_value` | every other mapped keyword | a value the schema rejects |
| `unmapped_keyword` | allowlist miss | a keyword with no mapping yet |

`unmapped_keyword` is a visible signal to extend the map, never a silent default: it is
what the generic message branch already implies, made greppable.

`code` is a pure function of `validator`, computed in the shared normalization layer
(`errors.py`, mirrored in `errors.ts`) beside the message table, so the two engines
cannot drift. The `unevaluatedProperties` message template added below emits the *same
string* as `additionalProperties` — one category, one code, one message.

Two naming points, because the word `code` is already taken twice nearby.
This `code` sits *inside* a record whose `kind` is `schema_violation`; it subdivides
that kind and does not compete with it.
It is also distinct from the `code:` field on shared vectors, which pins a record’s
`kind` — the vector field that clause 2 of Phase 2 removes for
`enforcement_unsupported`.

**The documented match surface becomes `kind` + `code` + `path`.** `validator` and
`validator_value` stay diagnostic, and message wording may improve in a minor.

### `enforcement_unsupported` becomes unreachable

Under the rule there is no shape the overlay must refuse: fragments are left alone and
roots close annotation-aware.
`EnforcementUnsupportedError` is never raised, and `_contains_open_properties` becomes
dead code.
Both are deleted, along with the `enforcement_unsupported` kind and the vector
`code` field naming it (see Decision Summary).

This also answers the issue’s fallback request ("raise when the schema is loaded"). It
is worth recording why that fallback is the *weaker* option, not just the unchosen one:
`enforcement_unsupported` and `schema_invalid` both classify as `outcome: "invalid"`
today, because `input_codes` in `ArtifactValidationResult.__post_init__` is limited to
`artifact_unreadable` and `artifact_invalid_utf8`. Moving schema-authoring failures to
their own outcome would change exit classes for `schema_invalid` too — a breaking change
to the result contract, for a code path this design removes.

### Parity work this newly exposes

Supporting these shapes makes four divergences reachable.
All four are measured, not predicted.

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
Add the template to both, emitting the identical string, so the two keywords that share
a `code` also share their wording.

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

Follows the golden-first parity process in [development.md](../../../development.md):
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
- Delete `_contains_open_properties`, `EnforcementUnsupportedError`, the
  `enforcement_unsupported` kind, and the vector `code` field naming it.
- Add the `unevaluatedProperties` message template to `errors.py`, emitting the same
  string as `additionalProperties`.
- Add the `code` enum and the keyword-to-code map to `errors.py`, and set `code` in
  `structural_error_record`.
- Update `apply_enforced_extras`’s docstring: it is the reference prose for the rule.

### Phase 3: TypeScript

- Mirror the closure rule in `canonicalize.ts`.
- Mirror the `code` enum and keyword-to-code map in `errors.ts`, alongside the matching
  message template.
- Generalize `collapseAdditionalProperties` to collapse on the `undeclared_property`
  code rather than a keyword list, renaming it for what it now does.
- Suppress ajv `if` wrapper records in `normalizeAjvError`’s caller.

### Phase 4: Documentation

- `docs/softschema-spec.md`, Status Values: the closure is no longer a single-keyword
  rule. State the applicator split, both keywords, and that fragments are never closed.
- `docs/softschema-guide.md` line 262: extend the parenthetical so the Step 5
  description stays true for composed schemas.
- Add a short “cross-field rules” example to the guide — the issue’s
  `decision: abandoned` requires `budget_spent` shape is the natural one, and its
  absence is part of why the limitation went unnoticed.
- `docs/softschema-spec.md`, error records: add the `code` table, and state which fields
  are the stable match surface and which are diagnostic.
- CHANGELOG: lead with the `validator`-to-`code` migration table under a heading that
  says it is breaking for consumers matching `validator`, then note that schemas
  previously refused now validate.
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
| `code` is stable across both closure keywords | vector assertion that a simple and a composed undeclared key both report `undeclared_property` |
| No keyword falls through unmapped | unit assertion that every keyword in the message table maps to a code other than `unmapped_keyword` |
| Engine-neutral records | golden corpus run twice via `SOFTSCHEMA_IMPL`, plus `cross-impl-diff.sh` |
| Known engine deviations | the `engine_deviations` vector section, where each runtime asserts its own record set exactly — covering the `dependentSchemas` record set and the pre-existing `anyOf` multiplicity, so drift on either side and any unlisted divergence still fail |

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
  At a composition root, no document silently becomes valid.
  Below one, two shapes the blanket refusal used to reject are now accepted — objects
  declared inline inside a fragment, and alternatives nested inside a fragment.
  Both are open by design and pinned as `enforcement_gaps` vectors.
- **Non-composed schemas are bit-identical.** Clause 3 keeps `additionalProperties` for
  them, which is why the golden corpus passes untouched.
- **Compiled schemas and `schema_sha256` are unaffected.** The overlay remains
  validation-time only.
- **Records gain a `code` field.** Additive for anyone reading records loosely, and the
  new field is what consumers should match on going forward.
- One behavioral widening deserves a maintainer’s eye: `unevaluatedProperties` is
  annotation-based, so a property named in an `if` matcher is *evaluated* when the
  matcher succeeds, and is therefore admitted.
  Given `if: {properties: {secret: {const: "x"}}}` with no `secret` in the root’s
  `properties`, `{"secret": "x"}` passes closure while `{"secret": "other"}` is
  rejected. This is correct 2020-12 behavior, it is narrow, and it is the price of
  annotation-aware closure — but it should be documented in the spec rather than
  discovered.

### Upgrade path

By maintainer direction this ships as a minor that may break a little, provided the
breakage is loud and the path out is written down.
One break is not loud, and it is the one the release notes must lead with.

A consumer matching `validator == "additionalProperties"` does not crash when a composed
schema starts reporting `unevaluatedProperties`. It silently stops matching — the branch
simply never fires again.
That is the single failure this change cannot make obvious from inside the library, so
the CHANGELOG carries the migration table and the spec documents `kind` + `code` +
`path` as the surface to match instead.

| Matching on | Before | After |
| --- | --- | --- |
| `validator == "additionalProperties"` | catches every undeclared key | misses composed schemas — **migrate** |
| `kind == "enforcement_unsupported"` | fires for composed schemas | never fires; the kind is gone |
| `code == "undeclared_property"` | not available | catches every undeclared key |

Everything else is loud: a removed exception class is an `ImportError`, and a removed
vector field fails the shared vector load.

## Decision Summary

| Decision | Rationale |
| --- | --- |
| Close with `unevaluatedProperties`, do not traverse `allOf` with `additionalProperties` | The issue’s first suggestion, read literally, reintroduces the bug the refusal guards. Verified against both engines. |
| Split applicators into alternatives and fragments | The existing code already draws this line; only its consequence changes. |
| Treat a fragment-declaring node as property-declaring | Otherwise the `composed_object` vector is enforced nowhere. |
| Never close inside a fragment | Closing an `if` matcher silently stops a conditional from firing — the worst failure mode available. |
| Keep the diagnostic at validation time | The refusal disappears; relocating it would require changing `schema_invalid`’s outcome class too. |
| Delete `enforcement_unsupported` rather than reserve it | It becomes unreachable and has no official surface: the string appears in no spec, guide, README, or changelog, and `EnforcementUnsupportedError` is exported by neither package. An output string is not a symbol — a consumer matching it loses that branch the moment emission stops, whether or not a constant remains in source. |
| Report the true keyword in `validator`, and add `code` for matching | Maintainer direction. `validator` is documented as the JSON Schema keyword, so normalizing it away would hide which closure fired; a softschema-owned category gives consumers something stable to match without that cost. |
| Support `dependentSchemas`, pinning engine deviations as documented diffs | Maintainer direction: functionally equivalent, language-native differences are fine when tests record them; Python goldens are the reference. |

## Implementation Notes

Landed as specified, with two deltas worth recording.

**The deviation mechanism is a vector section, not a checked-in diff.**
`cross-impl-diff.sh` compares CLI output, and no CLI fixture reaches the
`dependentSchemas` or `anyOf` divergences — both are library-level.
`engine_deviations` in `tests/vectors/hardening.yaml` pins each engine’s record set
separately, which is a stricter pin than a tolerated diff: drift *toward* agreement
fails too, so the entry cannot rot silently.
The three composed CLI cases were added to `cross-impl-diff.sh` regardless, and are
byte-identical.

**Review findings folded in.** The published review of PR #42 found three composition
shapes the first cut got wrong, all now fixed and pinned: a definition reached only
through composed references was closed lexically and rejected keys its sibling branch
declared (the `allOf: [{$ref: Base}, {properties: …}]` extension idiom, and the same
shape with `$ref` adjacent to `properties`); and `not` was treated as a declaration, so
a prohibition-only schema closed against everything.
Clause 4 and the `_REFERENCE_KEYWORDS` handling exist because of those.
Two shapes the review found *under*-enforced are deliberately left open and pinned as
`enforcement_gaps` vectors rather than fixed — see the spec’s “What `enforced` does not
close”.

**A sibling bug surfaced and was left out of scope** (`ss-p32o`). The same lexical
blindness affects `anyOf`/`oneOf` when a node declares its own `properties` alongside
alternatives that declare more — and the refusal never covered that shape, so it ships
today. Verified on `main`:
`{properties: {a}, anyOf: [{properties: {b}}, {properties: {c}}]}` rejects `{a, b}`,
which the raw schema accepts.
The root is fixable the same way, but the branch closure needs a maintainer decision
rather than a port, so it is tracked separately.

## Open Questions

*(none outstanding)*

1. ~~**Is `unevaluatedProperties`’s evaluation cost worth measuring?**~~ Measured: with
   the 0.6.2 memoization warm, a 20-property object costs ~113 µs/doc closed with
   `additionalProperties` and ~221 µs/doc closed with `unevaluatedProperties` — roughly
   2×, and only for composed schemas under `enforced`. Acceptable for a validation-time
   overlay on artifact-sized documents; revisit only if `enforced` moves onto a hot
   path.

## References

- GitHub issue [#41](https://github.com/jlevy/softschema/issues/41)
- [Minimal Softschema Hardening](../done/plan-2026-07-11-minimal-softschema-hardening.md),
  which introduced the refusal
- [softschema Spec](../../../softschema-spec.md), Status Values
- [JSON Schema 2020-12 Core](https://json-schema.org/draft/2020-12/json-schema-core.html),
  `unevaluatedProperties` and annotation collection
- [ajv unevaluatedProperties](https://ajv.js.org/json-schema.html#unevaluatedproperties)
- tbd `common-doc-guidelines`
- tbd `golden-testing-guidelines`

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
