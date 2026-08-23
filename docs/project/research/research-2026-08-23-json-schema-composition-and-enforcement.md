---
title: JSON Schema Composition, Field Dependencies, and Enforced Closure
description: >-
  Research into Draft 2020-12 field relationships, annotation-based closure,
  references and resources, Python jsonschema and TypeScript Ajv behavior, and the
  implications for softschema's enforced validation policy.
author: Joshua Levy with OpenAI Codex assistance
---
# Research: JSON Schema Composition, Field Dependencies, and Enforced Closure

**Date:** 2026-08-23

**Author:** Joshua Levy with OpenAI Codex assistance

**Status:** Complete

## Overview

This research supports the design review of softschema PR #42. The immediate change
replaces a blanket refusal to enforce composed schemas with an annotation-aware closure
overlay. The larger question is whether a validator can infer “declared fields” from an
arbitrary JSON Schema without changing the schema’s meaning.

That question crosses several boundaries:

- JSON Schema distinguishes assertions, applicators, and annotations.
  “Declared field” is a softschema policy term, not a JSON Schema term.
- Object keywords operate at an instance location.
  Composition and references can bring declarations from several schema objects to that
  same location.
- `$ref` resolves through a resource graph, not through a root-only map of `$defs` keys.
- Python `jsonschema` and TypeScript Ajv implement the same draft but expose different
  compilation, resource, and diagnostic surfaces.
- Pydantic and Zod add separate semantic-validation behavior that is not automatically
  represented by the compiled structural schema.

The core conclusion is that a general enforced-closure pass is a schema compiler, not a
local tree rewrite. Softschema should either require explicit closure in the authored
schema or define a restricted, checked enforcement profile.
It should not silently apply a partial approximation to every Draft 2020-12 schema.

## Questions to Answer

1. Which JSON Schema keywords express field presence, field dependencies, field
   evaluation, and closed-object behavior?
2. How do annotations propagate through `allOf`, `anyOf`, `oneOf`, conditionals, and
   references?
3. Where must `additionalProperties` or `unevaluatedProperties` be placed to avoid
   changing an existing schema’s meaning?
4. What reference and resource behavior must a transformation understand?
5. What do Python `jsonschema`, Ajv, Pydantic, and Zod support, and where do their
   public surfaces differ?
6. Which edge cases matter to softschema’s `status: enforced` contract?
7. What implementation and documentation boundary is sustainable for both runtimes?

## Scope

This document covers JSON Schema Draft 2020-12 object validation, in-place applicators,
annotations, references, embedded and supplied resources, and cross-field dependencies.
It compares the versions installed in this repository on 2026-08-23:

| Component | Version | Role |
| --- | --- | --- |
| Python `jsonschema` | 4.26.0 | Draft 2020-12 structural validation |
| Python `referencing` | 0.37.0 | URI-based schema-resource registry |
| Pydantic | 2.13.4 | Python model validation and schema generation |
| Ajv | 8.20.0 | TypeScript/JavaScript Draft 2020-12 validation |
| Zod | 4.4.3 | TypeScript model validation and schema generation |

The research does not attempt to define arbitrary business invariants, compare every
JSON Schema implementation, or design network schema retrieval.
Softschema’s closed in-memory resource policy remains a sound boundary.

## Findings

### “Declared” and “evaluated” are different concepts

JSON Schema does not have a general declaration table for object keys.
It has keywords that assert facts about an instance and keywords that apply subschemas.
Some object applicators also produce annotations identifying property names they
evaluated. Draft 2020-12’s `unevaluatedProperties` consumes those annotations.

This distinction matters because a property can be named without being evaluated:

```yaml
type: object
required: [account_id]
unevaluatedProperties: false
```

`{account_id: 42}` fails.
`required` asserts presence, but it does not apply a schema to the property value and
does not mark the property as evaluated.
Adding `properties: {account_id: true}` makes the intended declaration explicit.

The main object keywords have these roles:

| Keyword | Relationship expressed | Marks property values evaluated? | Closure consequence |
| --- | --- | --- | --- |
| `properties` | Apply a schema to each named property when present | Yes | Names can satisfy `unevaluatedProperties` |
| `patternProperties` | Apply schemas to every name matching each pattern | Yes | Matching names must not be treated as extras |
| `additionalProperties` | Apply a schema to names unmatched by sibling `properties` and `patternProperties` | Yes | Lexical; cannot see declarations in sibling schema objects |
| `unevaluatedProperties` | Apply a schema after adjacent in-place applicators have contributed annotations | It consumes and then produces evaluation information | Appropriate at a composition site |
| `required` | Require listed names to exist | No | A required name must still be declared or otherwise evaluated |
| `dependentRequired` | Require names when a trigger name exists | No | Presence dependency only; it does not declare either name |
| `dependentSchemas` | Apply a subschema to the whole object when a trigger name exists | Through the applied subschema | Behaves like conditional in-place composition |
| `propertyNames` | Validate each key string | No for property values | Does not make the corresponding values evaluated |
| `minProperties` / `maxProperties` | Constrain object cardinality | No | No effect on declared-key closure |

`patternProperties` patterns can overlap.
A property matching two patterns must satisfy both schemas.
A property can also match a literal `properties` entry and one or more patterns.
Any inferred closure policy must preserve those intersections.

The clean policy definition is therefore not “a key named anywhere.”
It is closer to “a property value evaluated by the successful schema evaluation at this
instance location.” If softschema wants `required` alone to count as a declaration, that
is an additional language rule and should be specified as such.

### Closure is an instance-location operation

`additionalProperties` is lexical.
It sees only `properties` and `patternProperties` in the same schema object.
It cannot see a key described by a sibling `allOf` branch or by a referenced schema.

`unevaluatedProperties` is annotation-aware.
It can see property evaluations contributed by adjacent in-place applicators, including
successful composition branches and references.
It therefore belongs at the schema object where those contributions meet.

```yaml
type: object
properties:
  a: {type: string}
allOf:
- properties:
    b: {type: string}
unevaluatedProperties: false
```

Here `{a: x, b: y}` is valid.
Placing `additionalProperties: false` at the root or in either branch rejects a field
declared by the other schema object.

The relevant unit is the instance location, not lexical ancestry in the schema document.
A `properties.child` subschema applies to a child instance location even when it is
written inside an `allOf` branch.
Conversely, two distant schema objects can apply to the same location through references
or composition. A boolean such as `in_fragment` can be a conservative implementation
guard, but it is not a full model of evaluation.

### Alternative branches are not necessarily complete descriptions

`allOf` requires every branch to succeed.
`anyOf` requires at least one, and the specification requires implementations collecting
annotations to examine every successful `anyOf` branch.
`oneOf` requires exactly one branch to succeed.

Closing `anyOf` or `oneOf` branches independently changes which branches succeed:

```yaml
anyOf:
- type: object
  required: [a]
  properties: {a: {type: string}}
- type: object
  required: [b]
  properties: {b: {type: string}}
```

The raw schema accepts `{a: x, b: y}` because both branches succeed.
Adding `additionalProperties: false` to each branch makes both fail.
The data contains only keys explicitly described by successful alternatives, yet closure
rejects it.

The reverse failure occurs with `oneOf`:

```yaml
oneOf:
- type: object
  properties: {a: {type: string}}
- type: object
  properties: {b: {type: string}}
```

The raw schema rejects `{a: x}` because both permissive branches succeed.
Closing each branch makes only the first succeed, so the transformed schema accepts data
the authored schema rejects.

This second result is more than over-strict closure: the transformation widens the
schema. A sound enforcement overlay needs both invariants:

1. It never makes a raw-invalid instance valid.
2. It makes a raw-valid instance invalid only because the instance contains a property
   that the declared-key policy classifies as undeclared.

`unevaluatedProperties: false` at the alternative’s parent preserves branch selection
and consumes annotations from the successful branch or branches.
A compiler may impose a convention that union branches are disjoint complete records,
but it must validate that convention rather than assume it for arbitrary schemas.

### Conditional dependencies are success-sensitive

`dependentRequired` is a presence assertion.
It is appropriate for relations such as “when `credit_card` is present,
`billing_address` is required,” but both names still need ordinary declarations if
closed-object behavior is desired.

`dependentSchemas` applies a subschema to the entire object when its trigger property is
present. Its successful property annotations can flow to an adjacent
`unevaluatedProperties` keyword.

`if` chooses `then` or `else`. An `if` subschema that succeeds can contribute evaluation
annotations; a failing matcher does not.
A property named only inside the matcher can therefore be evaluated for one value and
unevaluated for another.
Schema authors should normally declare matcher fields at the surrounding object and use
`if` only to select the dependent constraint.

`not` is different. It inverts validation and does not export the negated subschema’s
annotations. A property appearing only under `not` is a prohibition, not a declaration.

These rules explain why branch-local closure is dangerous.
Adding closure inside an `if` matcher can change whether the matcher fires; adding it
inside a conditional fragment can reject declarations contributed at the same instance
location by the surrounding schema.

### References form a resource graph, not a `$defs` lookup table

`$ref` and `$dynamicRef` are in-place applicators.
A Draft 2020-12 `$ref` is a URI reference, may have siblings, and resolves against the
current base URI. Valid targets include:

- JSON Pointer fragments such as `#/$defs/Address`;
- plain-name fragments created by `$anchor`;
- embedded resources whose `$id` changes the base URI;
- explicitly supplied external resources; and
- dynamically selected anchors reached through `$dynamicRef`.

JSON Pointer tokens also require `~0` and `~1` escaping.
Nested `$defs` entries and subschemas outside `$defs` can be reference targets.
Root-only string matching handles only one convenient spelling of one reference
topology.

Definitions are reusable schemas, not classes that own one global closed/open state.
The same target can be applied alone at one instance location and combined with sibling
constraints at another.
Closing the definition object globally makes those contexts interfere.
Even an unused standalone reference elsewhere in the schema can then change a composed
site’s verdict.

The more reliable default is to keep reusable targets open and place annotation-aware
closure at each application site that needs it.
That still requires reference resolution to determine whether a site describes a
structured object. For dynamic references and unknown extension applicators, static
resolution may be impossible or outside the supported profile; the validator should
report that boundary rather than guess.

An explicit closure keyword is also scoped to an instance site.
For example, `{$ref: ..., unevaluatedProperties: true}` opts that referring site out.
It cannot do so if a transformation has already inserted `additionalProperties: false`
into the shared target.

### Python and TypeScript support the draft but expose different mechanics

Python `jsonschema.Draft202012Validator` supports Draft 2020-12 and accepts an immutable
`referencing.Registry` for already loaded resources.
The registry does not retrieve remote schemas unless the caller supplies retrieval
behavior. This fits softschema’s offline boundary.

Ajv requires the `Ajv2020` class for Draft 2020-12. It supports `unevaluatedProperties`,
`$dynamicAnchor`, and `$dynamicRef`; schemas can be registered with `addSchema`. Ajv
does no I/O unless the caller supplies a loader.
It compiles schemas to JavaScript, while Python `jsonschema` interprets them.

The validation verdicts agree for ordinary supported schemas, but error enumeration and
schema-compilation failure surfaces differ:

- Python emits one `required` error per missing property.
  Its native message names the missing property, while `validator_value` contains the
  whole `required` array.
- Ajv emits one `required` error per missing property and provides the name in
  `params.missingProperty`.
- Python combines several additional or unevaluated keys into one error.
  Ajv emits one error per key and identifies it in `params.additionalProperty` or
  `params.unevaluatedProperty`.
- Python reports a parent `anyOf` error with branch failures under
  `ValidationError.context`. Ajv emits the branch errors and the parent error in one
  flat array when `allErrors` is enabled.
- Native regular-expression engines differ.
  A portable profile must check every schema resource before either validator compiles
  it.

Normalization should preserve semantic details before collapsing runtime-specific
records.
A stable `{kind, code, path}` tuple cannot distinguish two missing properties at
the same object path.
A portable `property` or sorted `properties` detail field can.

### Pydantic and Zod add a separate semantic layer

Pydantic and Zod can express cross-field rules that are awkward or impossible in the
portable structural profile.
Pydantic model validators and Zod refinements/checks should remain semantic validation,
reported separately from JSON Schema results.

Their object defaults also matter:

- Pydantic’s default model ignores extra input and emits an open object schema.
  Setting `extra="forbid"` rejects extras and emits `additionalProperties: false`.
- A normal Zod object strips unknown keys during parsing.
  `z.strictObject` rejects them, while `z.looseObject` preserves them.
- Zod’s JSON Schema conversion emits no `additionalProperties` for a normal object in
  `io: "input"` mode, but emits `additionalProperties: false` in output mode.
  `z.strictObject` is closed in either mode.
- Pydantic commonly emits nested models into root `$defs` and represents a nullable
  model as `anyOf: [{$ref: ...}, {type: "null"}]`. Zod can inline or extract reused
  schemas depending on conversion options.

These are related but not interchangeable policies.
A contract marked `enforced` is not actually closed if structural validation is skipped
and the only semantic model ignores or strips extras.
An API must either require a structural schema for enforced status, derive one in
memory, or explicitly apply a strict semantic policy in each runtime.

## Softschema PR #42 Evidence

The following probes compare each authored schema with the PR-head validation-time
overlay. Except where noted, Python and TypeScript produced the same verdict.
“Raw” means the authored Draft 2020-12 schema; “enforced” means the current softschema
overlay.

| Shape and instance | Raw | Enforced | Interpretation |
| --- | --- | --- | --- |
| Simple `properties`, plus `bogus` | valid | invalid | Intended narrowing |
| Two `allOf` branches declaring `a` and `b`; `{a, b}` | valid | valid | PR’s central fix works |
| Two successful `anyOf` branches declaring `a` and `b`; `{a, b}` | valid | invalid | Branch-local closure rejects declared keys |
| Two overlapping `oneOf` branches; `{a}` | invalid | valid | Overlay changes branch selection and widens the schema |
| One `$defs` target used both standalone and in `allOf`; composed `{street, extra}` | valid | invalid | Global target closure makes use sites interfere |
| `$ref` with sibling `unevaluatedProperties: true`; `{street, extra}` | valid | invalid | Explicit opt-out cannot override target mutation |
| `patternProperties`-only object with one unmatched key | valid | valid | Enforced mode does not close the structured pattern map |
| `$ref` plus sibling `patternProperties`; matching extra key | valid | invalid | Target closure cannot see the sibling pattern annotation |
| `allOf` extension through `$anchor` | valid | invalid | Root-only pointer resolver misses a valid target form |
| Extension through nested `$defs` | valid | invalid | Root-only definition indexing misses nested targets |
| Object supplied through the public external `resources` map, plus extra key | valid | valid | Resources bypass the overlay |
| `$defs` workaround referenced below a conditional fragment, with nested extra key | valid | valid | The documented workaround does not restore closure |

A plain-name `$dynamicRef` probe was also engine-sensitive: Python accepted the raw
schema and rejected the overlaid instance, while Ajv failed compilation with a stack
overflow for both. This is a warning against claiming dynamic-reference support in the
transformer based only on keyword recognition.
A dedicated official-conformance fixture is needed before that topology belongs in an
enforced profile.

The resource path exposes a second inconsistency.
With an external resource containing the Python-only pattern `(?P<x>a)`, Python built
the validator and accepted `"a"`; Ajv returned `schema_invalid` for an invalid regular
expression. The root schema is checked against softschema’s portable regex subset, but
supplied resources are not.
The same prepare-and-check pipeline must cover the entire graph.

Finally, an `enforced` Python `Contract` with only a default Pydantic model accepted
`{known: 1, bogus: 2}`. Structural validation reported `inferred_via_model`, and
semantic validation ignored the extra key.
The low-level `validate_values` and `validateValues` APIs also provide no status or
strict-extras option.

## Key Insights

### Enforcement is a new language profile

The authored schema permits additional properties when no closure keyword says
otherwise.
Softschema’s enforced mode deliberately assigns a stronger meaning to a subset
of schema shapes. That is a language profile layered on Draft 2020-12, not merely
“turning on” a dormant JSON Schema option.

The profile needs a normative definition of:

- which keywords declare or evaluate a property;
- which applicator and reference shapes it supports;
- where closure is inserted;
- how explicit closure opts out;
- which resources are in scope; and
- what happens when the transformer cannot prove a safe placement.

Without that definition, examples and implementation heuristics become the de facto
language, and equivalent JSON Schema spellings can receive different verdicts.

### A schema graph must be prepared as one unit

Parsing, portable-value checks, metaschema checks, regex checks, resource identity,
reference resolution, enforced-profile analysis, overlay application, and validator
compilation are one pipeline.
Applying some stages only to the root allows supplied resources to bypass both policy
and parity checks.

The pipeline can remain offline.
It should operate on the root plus every explicitly loaded resource, index the same URI
and anchor identities the runtime validators use, and return one structured schema
failure before document validation begins.

### Transformation-shape tests are insufficient

Asserting that a node received `additionalProperties` or `unevaluatedProperties` pins an
implementation choice, not semantic correctness.
The primary oracle should compare document verdicts before and after transformation.

The strongest small test set is metamorphic:

- inline schema versus the same schema reached by JSON Pointer, anchor, or external URI;
- one use of a definition versus adding an unused second use;
- `allOf`, `anyOf`, and `oneOf` versions of the same field set;
- direct `properties` versus equivalent `patternProperties`;
- explicit closure at the target versus at the application site; and
- root resource versus the same schema supplied through `resources`.

For every case, assert both “never widen” and “narrow only for a demonstrably undeclared
key.” Run the same vector through Python and TypeScript.

## Comparison Matrix

| Design dimension | Explicit authored closure | Checked overlay profile | General graph transformer |
| --- | --- | --- | --- |
| Schema remains self-describing outside softschema | Yes | No | No |
| `status` can tighten without regeneration | No | Yes | Yes |
| Implementation complexity | Low | Moderate | High |
| Handles arbitrary Draft 2020-12 | Whatever the author writes | No; unsupported shapes fail explicitly | Aspirational; dynamic and extension vocabularies remain difficult |
| Cross-runtime parity risk | Lowest | Bounded by profile and vectors | Highest |
| Compatible with current product direction | Requires policy change | Yes | Yes, but disproportionate |
| Recommended use | Long-term schema contract | Near-term softschema policy | Do not pursue without a concrete consumer |

## Options Considered

### Option A: Require explicit closure in compiled schemas

The source model or hand-authored schema emits `additionalProperties` or
`unevaluatedProperties` in the correct places.
`status: enforced` requires that closure to be present rather than synthesizing it.

**Advantages:**

- The schema’s meaning is portable to every Draft 2020-12 validator.
- The schema digest covers the real boundary contract.
- References and composition use native annotation semantics without a second compiler.
- Failure is attributable to the authored schema, not a hidden runtime rewrite.

**Costs:**

- Flipping status may require model configuration and schema regeneration.
- Pydantic and Zod source policies must be aligned deliberately.
- Existing open schemas need a migration.

### Option B: Define a checked enforced-overlay profile

Keep the validation-time overlay, but analyze the complete resource graph first.
Apply closure only for supported shapes and return a stable `enforcement_unsupported`
schema error for everything else.

**Advantages:**

- Preserves the current status-promotion workflow.
- Keeps implementation and parity risk bounded.
- Makes unsupported hand-authored or dynamic shapes explicit.
- Allows the profile to grow one conformance vector at a time.

**Costs:**

- The compiled schema alone does not describe effective enforced behavior.
- A support matrix becomes part of the public language contract.
- Reference-site analysis is still required for reusable definitions.

### Option C: Implement a general Draft 2020-12 graph transformer

Resolve every reference form, model instance locations, understand all in-place
applicators and extension vocabularies, and insert closure wherever a property can be
proven declared.

**Advantages:**

- Broadest acceptance of hand-authored schemas.
- Fewer explicit unsupported results if implemented correctly.

**Costs:**

- Reimplements a substantial part of validator evaluation.
- `$dynamicRef`, recursive graphs, custom vocabularies, and success-dependent
  annotations make static analysis complex.
- Two independent implementations multiply correctness and maintenance risk.
- A partial implementation looks successful while returning wrong verdicts.

### Eliminated option: Enforce extras only in Pydantic or Zod

This is not language-neutral, does not cover schema-only consumers, and inherits
different extra-key behavior from the two model libraries.
Semantic strictness can be an additional defense but cannot define the portable
contract.

## Recommendations

Use Option B for the immediate correction and treat Option A as the simpler long-term
contract.

1. Restore a structured unsupported result until each composition family has semantic
   before/after vectors.
   Do not replace an honest refusal with a wrong verdict.
2. Move the overlay out of the canonicalization module into a schema-graph preparation
   component that accepts the root and supplied resources together.
3. Define the enforced profile in the main spec.
   Base declarations on successful property-evaluation annotations; include
   `patternProperties`; state explicitly that `required`, `dependentRequired`, and
   `propertyNames` do not evaluate values.
4. Treat `anyOf` and `oneOf` as in-place composition sites.
   Preserve branch selection and close with `unevaluatedProperties` at the parent when
   the profile can prove that is safe.
5. Keep reusable definitions open by default.
   Close at reference application sites, and honor explicit closure at that same
   instance site. Reject reference topologies the profile cannot resolve.
6. Prepare every resource uniformly: portable value and regex checks, metaschema checks,
   identity indexing, profile analysis, overlay, then compilation.
7. Decide what `status: enforced` guarantees when no structural schema is bound.
   Either require or derive a schema, or rename/document the status as advisory in that
   path.
8. Add stable offending-property details to structural errors before normalizing engine
   multiplicity.
9. Make semantic outcome vectors the primary enforcement tests.
   Keep transform-shape tests only as implementation-level supplements.

## Documentation Requirements

The normative documentation should contain one support matrix rather than distributing
behavior across a spec, two design docs, code docstrings, an active plan, and vector
comments. At minimum it should state:

- supported object declaration keywords;
- supported in-place applicators;
- supported reference spellings and resource boundaries;
- explicit closure precedence at an instance site;
- known under-enforcement and over-enforcement, if any;
- the structural-schema requirement for enforced status;
- parity guarantees for verdicts versus diagnostic record sets; and
- verified workarounds for unsupported shapes.

Every referenced tracking ID should resolve on the reviewed branch.
A limitation without a real issue is not tracked merely because a comment names an ID.

## Implementation Outcome

The stacked remediation implements Option B in commit `9d69517`. Both runtimes now
prepare the root and supplied resources as one checked offline graph, keep reusable
targets open, and close structured application sites independently.
The implementation covers static pointers, escaped pointer tokens, anchors, nested
definitions, embedded resource identities, supplied resources, literal and pattern
declarations, alternatives, conditionals, and dependent schemas within the profile
specified in the main spec.

The implementation also makes the boundary explicit.
Dynamic references and the four instance-location shapes for which static analysis
cannot prove safe annotation flow return `enforcement_unsupported` with a stable reason.
Enforced model-only calls return `enforced_schema_required`. Missing and
undeclared-field errors carry the affected `property`, with one record per field.

Shared semantic vectors now compare raw and enforced outcomes across both runtimes,
including reference/resource equivalents and each unsupported reason.
Python and TypeScript agree on checked-profile verdicts.
The remaining native-engine record-set differences are listed and asserted separately
under `engine_deviations`; they are not treated as verdict differences.

## Next Steps

- [x] Resolve alternative-branch semantics (`ss-vy4t`).
- [x] Replace global definition closure with application-site policy (`ss-iq9w`).
- [x] Prepare and validate the complete schema resource graph (`ss-qr8j`).
- [x] Define `patternProperties` declaration behavior (`ss-w78w`).
- [x] Make enforced status a real API guarantee (`ss-4est`).
- [x] Preserve offending field identity in structural errors (`ss-5rjo`).
- [x] Reconcile the spec, design docs, examples, vectors, docstrings, and issue links
  (`ss-pq0m`).

## Methodology

The research combined four evidence sources:

1. Normative Draft 2020-12 core and validation specifications.
2. Official documentation for Python `jsonschema`/`referencing`, Ajv, Pydantic, and Zod.
3. Static inspection of the PR-head Python and TypeScript implementations, tests,
   vectors, and main design documents.
4. Paired runtime probes against the dependency versions installed from this
   repository’s locks. Probes compared raw and overlaid verdicts and inspected native
   error details.

The probes are diagnostic evidence, not a replacement for the official JSON Schema Test
Suite. Dynamic-reference behavior needs a dedicated conformance fixture before a support
decision.

## References

- [JSON Schema Draft 2020-12 Core](https://json-schema.org/draft/2020-12/json-schema-core)
- [Draft 2020-12 annotations](https://json-schema.org/draft/2020-12/json-schema-core#section-7.5)
- [Draft 2020-12 schema references](https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.3)
- [Draft 2020-12 in-place applicators](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2)
- [Draft 2020-12 `anyOf`](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.2)
- [Draft 2020-12 `unevaluatedProperties`](https://json-schema.org/draft/2020-12/json-schema-core#section-11.3)
- [JSON Schema conditional validation](https://json-schema.org/understanding-json-schema/reference/conditionals)
- [Python `jsonschema` referencing](https://python-jsonschema.readthedocs.io/en/stable/referencing/)
- [Python `jsonschema` error model](https://python-jsonschema.readthedocs.io/en/stable/errors/)
- [Ajv Draft 2020-12 support and object keywords](https://ajv.js.org/json-schema.html)
- [Ajv schema management and resources](https://ajv.js.org/guide/managing-schemas.html)
- [Ajv options](https://ajv.js.org/options)
- [Pydantic model configuration](https://docs.pydantic.dev/latest/api/config/)
- [Pydantic JSON Schema generation](https://docs.pydantic.dev/latest/concepts/json_schema/)
- [Pydantic model validators](https://docs.pydantic.dev/latest/concepts/validators/#model-validators)
- [Zod JSON Schema conversion](https://zod.dev/json-schema)
- [Zod objects and refinements](https://zod.dev/api)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
