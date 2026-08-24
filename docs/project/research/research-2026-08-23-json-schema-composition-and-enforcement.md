---
title: JSON Schema Composition, Field Dependencies, and Undeclared Properties
description: >-
  A first-principles guide to JSON Schema evaluation and draft history, followed by
  research into Draft 2020-12 field relationships, annotation-based undeclared-property
  rejection, object and array child applicators, references and resources, Python
  jsonschema and TypeScript Ajv behavior, and the implications for softschema's enforced
  validation policy.
author: Joshua Levy with OpenAI Codex assistance
---
# Research: JSON Schema Composition, Field Dependencies, and Undeclared Properties

**Date:** 2026-08-23

**Author:** Joshua Levy with OpenAI Codex assistance

**Status:** Complete

## Overview

JSON is a data format for six kinds of value: `null`, booleans, numbers, strings,
arrays, and objects.
**JSON Schema** is a declarative language for describing which JSON values an
application accepts.
A validator receives two inputs—a schema and the JSON value being checked—and evaluates
whether that value satisfies the schema.
JSON Schema’s `integer` type describes numbers whose mathematical value has no
fractional part; it is not a seventh JSON value kind.

softschema uses JSON Schema as the portable structural contract for the YAML payload in
a Markdown artifact.
YAML is an authoring syntax here; after parsing, the payload and schema must have the
same data model as JSON. The difficult part of `status: enforced` is deciding which
object properties count as part of that contract when several subschemas describe the
same object.

This document uses **object closure** as shorthand for one scoped rule: at a single
object instance location, reject each present property whose value is not evaluated by
any successful applicable schema.
`additionalProperties: false` and `unevaluatedProperties: false` are the two relevant
JSON Schema mechanisms.
Closing an object does not mutate the data or automatically close every nested object.
Raw JSON Schema remains open unless the author supplies such a keyword; softschema’s
`status: enforced` policy inserts one at supported object locations during validation.

## JSON Schema From First Principles

### An instance is the value being checked

The JSON value being validated is called the **instance**. It can be a whole document or
one value nested inside a document.
JSON objects are string-keyed mappings; each key-value pair is a **property**. “Field”
is common application terminology, but “property” is the precise JSON and JSON Schema
term.

A **schema** is itself JSON. In modern drafts it is either an object or a boolean:

- `{}` and `true` accept every instance.
- `false` rejects every instance.
- A schema object uses named **keywords** to describe or constrain an instance.

softschema’s compiled schemas are often written as YAML for readability.
The following YAML is equivalent to a JSON Schema object:

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
type: object
properties:
  account_id: {type: integer}
  display_name: {type: string}
required: [account_id]
additionalProperties: false
```

The schema has five independent meanings:

- `$schema` selects the Draft 2020-12 dialect.
- `type: object` rejects non-object instances.
- `properties` validates `account_id` and `display_name` when they are present.
- `required` makes `account_id` mandatory.
- `additionalProperties: false` rejects every other property name.

The independence is important.
`properties` does not make a property required, and `required` does not validate its
value. Object-specific keywords also do not imply `type: object`; they simply have no
effect on a non-object instance.
A robust schema usually states the intended type explicitly.

| Instance | Result | Reason |
| --- | --- | --- |
| `{"account_id": 42}` | valid | The required property is present and is an integer |
| `{}` | invalid | `account_id` is required |
| `{"account_id": "42"}` | invalid | JSON Schema does not coerce the string to an integer |
| `{"account_id": 42, "nickname": "Al"}` | invalid | `nickname` is an additional property |

### Validation evaluates; it does not construct or mutate

Evaluation recursively applies the schema to the instance.
At the root, the schema above applies to the whole object.
A schema nested inside another schema is a **subschema**. Paths can be written as JSON
Pointers, a slash-separated location syntax: the subschema at schema location
`/properties/account_id` applies to the child value at instance location `/account_id`.
That distinction between a **schema location** and an **instance location** becomes
central once schemas compose.

JSON Schema validation does not, by itself:

- parse JSON or YAML;
- coerce a string into a number;
- insert a `default` value;
- remove unknown properties;
- instantiate a Python or TypeScript class; or
- run arbitrary application logic.

It produces a validity result and may produce annotations and diagnostics.
Parsing, normalization, model construction, and business rules are separate application
layers. This is why a Pydantic or Zod model can behave differently from the JSON Schema
it generates.

### A dialect defines the language being evaluated

A JSON Schema release is a **dialect**: a set of keywords and their exact semantics.
The root `$schema` URI identifies the dialect and its **meta-schema**, which is a schema
for checking schemas.
Without `$schema`, a validator must be configured with a dialect or choose a default,
which can change the meaning of the document.

Draft 2020-12 also organizes keywords into **vocabularies**. A vocabulary groups related
keywords, such as core identifiers, validation assertions, applicators, or annotations.
Custom dialects can choose vocabularies, so recognizing a keyword’s spelling is not
enough without knowing its dialect and vocabulary.

### Keywords have different jobs

The following categories prevent several common misunderstandings:

| Role | What it does | Examples |
| --- | --- | --- |
| Core organization and identity | Selects a dialect, stores subschemas, or identifies schema resources and locations | `$schema`, `$id`, `$anchor`, `$defs` |
| Assertion | Contributes a pass or fail condition | `type`, `required`, `minimum`, `minProperties` |
| Applicator | Applies one or more subschemas to the current or a child instance location | `properties`, `items`, `allOf`, `if`, `$ref` |
| Annotation | Attaches information for tools without normally changing validity | `title`, `description`, `default`, `deprecated` |

Applicators may also produce **evaluation annotations** that record which object
properties or array elements their subschemas evaluated.
These internal annotations are not the same as descriptive keywords such as `title`.
Draft 2020-12’s `unevaluatedProperties` and `unevaluatedItems` use them to find values
that no successful applicable subschema has covered.

### Object keywords describe presence, values, names, and rejection separately

The `properties` keyword is open by default: it ignores property names that it does not
list. Other object keywords may still constrain them.
These keywords divide responsibility rather than building one class-like field
declaration table.

| Keyword | Relationship expressed | Evaluates property values? |
| --- | --- | --- |
| `properties` | Apply a subschema to each named property when present | Yes |
| `patternProperties` | Apply a subschema for every regular expression that matches a property name | Yes; every matching pattern applies |
| `required` | Require listed property names to be present | No |
| `dependentRequired` | When one property is present, require other names | No |
| `dependentSchemas` | When one property is present, apply a subschema to the whole object | Through the applied subschema |
| `propertyNames` | Validate each property name as a string | No; it does not evaluate the corresponding values |
| `minProperties` / `maxProperties` | Constrain the number of properties | No |
| `additionalProperties` | Apply a subschema to values unmatched by sibling `properties` and `patternProperties` | Yes |
| `unevaluatedProperties` | Apply a subschema to values not evaluated by relevant successful schemas | Yes |

The distinction between the last two rows is the source of the undeclared-property
problem in composed schemas:

- `additionalProperties` is **lexical**. It sees only `properties` and
  `patternProperties` beside it in the same schema object.
- `unevaluatedProperties` is **annotation-aware**. It can account for successful
  evaluations contributed through adjacent composition and references.

Both keywords take a schema, not merely a boolean.
Setting either to `false` rejects the properties in its domain; setting it to another
schema validates those property values against that schema.

### Composition combines constraints, not object definitions

An applicator’s subschema may apply to the same instance location as its parent.
These are **in-place applicators**. The boolean composition keywords are the simplest
examples:

| Keyword | Validity rule |
| --- | --- |
| `allOf` | Every subschema must succeed |
| `anyOf` | One or more subschemas must succeed |
| `oneOf` | Exactly one subschema must succeed |
| `not` | Its subschema must fail |

`allOf` is logical AND, not object-oriented inheritance or a merge operation.
Each branch receives the complete instance and retains its own rules.
An `additionalProperties: false` inside one branch therefore rejects properties
described only by another branch.

Conditional applicators are also in-place.
`if` evaluates a matcher and selects `then` or `else`; `dependentSchemas` applies a
whole-object subschema when its trigger property is present.
Which branches succeed determines both validity and which evaluation annotations are
available. Annotations below `not` do not escape the negated schema.

### Child applicators can overlap

Other applicators move evaluation to child locations:

- `properties` and `patternProperties` apply schemas to object-property values;
- `prefixItems` applies schemas to specific array positions;
- `items` applies one schema to array positions after `prefixItems`; and
- `contains` tests array elements and can constrain the number of matches with
  `minContains` and `maxContains`.

Child locations are not necessarily independent.
A literal property and every matching pattern all apply to the same value.
An array element can be evaluated by `items` and also tested by `contains`. In Draft
2020-12, elements that satisfy `contains` count as evaluated for `unevaluatedItems`. A
transformation that closes each child subschema in isolation can therefore change an
intersection or change which elements match.

### References turn the schema tree into a resource graph

`$defs` is a storage location for reusable subschemas; putting a schema there does not
apply it. `$ref` applies a referenced schema at the current instance location.
It is an in-place applicator, not a textual include, class import, or inheritance
mechanism.

A reference is a URI reference resolved against the current base URI. It can point to a
JSON Pointer such as `#/$defs/Address`, a named `$anchor`, an embedded resource whose
`$id` establishes a new base URI, or a separately supplied resource.
References can be recursive.
The effective structure is therefore a graph of resources and application sites, even
when the source text is one YAML tree.

This distinction matters for transformation.
A reusable target can be applied alone in one place and combined with sibling
constraints in another.
Mutating the shared target to satisfy one use site also changes every other use site.

## How JSON Schema Reached Draft 2020-12

JSON Schema has evolved through released **drafts**. In this context,
[“draft” names a completed release](https://json-schema.org/learn/glossary#draft), not
an unfinished proposal.
Schemas should identify a specific draft because later dialects can add keywords or
change semantics.

The history most relevant to composition and undeclared properties is:

| Release | Relevant evolution |
| --- | --- |
| [Drafts 0–3 (2009–2010)](https://json-schema.org/specification-links) | The first IETF Internet-Draft line established a schema language for JSON values. |
| [Draft 4 (2013)](https://json-schema.org/specification-links#draft-4) | The specification separated core, validation, and JSON Reference documents. The combination of `$ref`, `allOf`, and lexical `additionalProperties` already made closed-schema reuse difficult. |
| [Draft 6 (2017)](https://json-schema.org/draft-06/json-schema-release-notes) | `id` became `$id`; boolean schemas became valid everywhere; `propertyNames`, `contains`, and `const` were added. Its release notes explicitly documented that `additionalProperties` could not see across composed reusable schemas and deferred a general solution. |
| [Draft 7 (2018)](https://json-schema.org/draft-07/json-schema-release-notes) | `if`/`then`/`else` added direct conditional evaluation, and the specification clarified the assertion, applicator, and annotation model. |
| [Draft 2019-09](https://json-schema.org/draft/2019-09/release-notes) | Numbered meta-schema names changed to year-month identifiers. This release organized keywords into vocabularies, formalized annotation and output handling, allowed `$ref` siblings, renamed `definitions` to `$defs`, split `dependencies`, and introduced `unevaluatedProperties` and `unevaluatedItems`. |
| [Draft 2020-12](https://json-schema.org/draft/2020-12/release-notes) | Tuple validation changed from array-form `items` plus `additionalItems` to `prefixItems` plus `items`; `$dynamicRef` and `$dynamicAnchor` replaced the narrower recursive-reference keywords; and successful `contains` matches were defined as evaluated array items. The unevaluated keywords moved into their own vocabulary. |

Draft 5 sometimes appears in older material, but it was a cleanup of Draft 4 without a
new meta-schema or new validation behavior.
Starting with 2019-09, year-month names avoid confusion between sequential meta-schema
names and independently numbered IETF documents.
The final Draft 2020-12 specification documents were published in June 2022.

This progression explains why rejecting undeclared properties across composed schemas is
subtle rather than accidental.
The lexical behavior of `additionalProperties` preserves the meaning of a subschema
wherever it is reused, but it cannot see declarations supplied elsewhere.
`unevaluatedProperties` was added later to close an object *after* successful in-place
evaluations have contributed annotations.
It is an evaluation mechanism, not a static union of every property name found in the
schema text.

## The softschema Enforcement Problem

An object schema using `properties` remains open to unmatched names unless another
keyword constrains them.
softschema deliberately gives `status: enforced` a stronger meaning: supported object
sites that declare structure should reject properties left outside the contract.
The validator therefore inserts an undeclared-property rule at validation time even when
the compiled schema is silent about it.

The design question is whether that overlay can infer “declared fields” from an
arbitrary Draft 2020-12 schema without changing any other part of the authored schema’s
meaning. “Declared field” is a softschema policy term, not a JSON Schema term.
The closest native concept is a property value evaluated by a successful applicable
schema at the same instance location.

That question crosses three layers:

1. Draft 2020-12 defines assertions, applicators, annotations, and reference resolution.
2. softschema may insert `additionalProperties: false` or `unevaluatedProperties: false`
   over the authored structural schema during validation.
3. Pydantic and Zod may add coercion, unknown-key handling, and cross-field rules that
   are not represented identically in JSON Schema.

The core conclusion is that a general pass that inserts undeclared-property rejection is
a schema compiler, not a local tree rewrite.
softschema should either require the author to supply that rule or publish a restricted
support matrix and reject every shape outside it.
It should not silently apply a partial approximation to every Draft 2020-12 schema.

### Compatibility with version 0.6.2

The ability to validate previously refused `allOf`, conditional, and dependent-schema
shapes is additive, but the complete change is not wholly backward-compatible.

| Surface | Version 0.6.2 | After the PR #42 and #44 stack | Compatibility |
| --- | --- | --- | --- |
| Supported `allOf`, `if`/`then`/`else`, and `dependentSchemas` object shapes | Refuses the composed schema before returning a document verdict | Returns the schema’s real valid or invalid verdict and rejects undeclared properties | Additive validation support |
| `anyOf`, `oneOf`, and reusable `$ref` targets | Can insert `additionalProperties: false` inside alternatives or shared targets, changing branch selection or making use sites interfere | Leaves alternatives and reusable targets unchanged and inserts the rule at a supported parent or reference application site | Correctness fix; verdicts can change for affected edge cases |
| Plain enforced object schemas | Rejects undeclared properties | Preserves that validity behavior, with more specific error records | Verdict-compatible; diagnostic API changes |
| `status: enforced` with a semantic model but no structural schema | Can succeed after model validation alone | Returns `enforced_schema_required` | Intentional breaking correction |
| Supplied schema resources | Can bypass root preprocessing or rely on engine-specific retrieval behavior | Every supplied resource is checked and registered with the root in one offline resource graph | Stricter and potentially breaking |
| Shapes whose safe transformation is not proved | Version 0.6.2 broadly refuses composed shapes; the base PR attempted some unsafe ones | Returns `enforcement_unsupported` with a stable reason instead of guessing | No loss relative to 0.6.2; a safety correction relative to the base PR |
| `soft` and `permissive` validation | Existing behavior | Unchanged | Compatible |
| Compiled schema bytes and `schema_sha256` | Existing output | Unchanged because insertion happens only during validation | Compatible |

## Research Questions

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

This document covers JSON Schema Draft 2020-12 object and array validation, in-place and
child applicators, annotations, references, embedded and supplied resources, and
cross-field dependencies.
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
softschema’s closed in-memory resource policy remains a sound boundary.

## Detailed Findings

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

`patternProperties` patterns can overlap.
A property matching two patterns must satisfy both schemas.
A property can also match a literal `properties` entry and one or more patterns.
Any inferred closure policy must preserve those intersections.

The clean policy definition is therefore not “a key named anywhere.”
It is closer to “a property value evaluated by the successful schema evaluation at this
instance location.” If softschema wants `required` alone to count as a declaration, that
is an additional language rule and should be specified as such.

### Undeclared-property rejection applies at one instance location

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

### Child applicators can co-describe one child location

In-place composition is not the only way several schema objects can describe the same
instance location. Sibling child applicators can converge on one child:

- a literal `properties` entry and every matching `patternProperties` pattern all apply
  to the same property value;
- every matching pair of `patternProperties` patterns applies together; and
- `items` or `prefixItems` can apply to an array element that `contains` also tests.

Closing the value schemas independently loses the same information that branch-local
closure loses under `allOf`. For example, if a literal property’s object schema declares
`x` and a matching pattern’s object schema declares `y`, adding
`additionalProperties: false` to both rejects `{x, y}` even though the authored
intersection accepts it.

Array applicators add match selection.
`contains` does not merely validate a known element; it decides which elements count
toward `minContains` and `maxContains`. Adding closure inside its subschema can change
that set. Closing an `items` object independently can also reject a field evaluated by
the successful `contains` schema.
By contrast, `prefixItems` and `items` cover disjoint index ranges in Draft 2020-12, so
their element schemas can be closed independently when `contains` is absent.

The `status: enforced` support matrix therefore needs a child co-evaluator rule as well
as an in-place applicator rule: infer closure only when one structured evaluator
describes the child location.
Literal-pattern overlap can be detected by testing the literal name.
Proving that pattern pairs are disjoint is not practical portably, so independently
closed structured pattern pairs should be refused conservatively.

Context-sensitive composition references require another graph check.
Leaving an `allOf`, `anyOf`, `oneOf`, `dependentSchemas`, conditional, `not`, or
`contains` subschema lexically unchanged is insufficient if a `$ref` inside it reaches a
reusable target whose nested schemas are changed by the global overlay.
The same problem occurs when a `$ref` has validation siblings at its application site.
That indirect mutation can change an intersection, branch or match selection, or
conditional success.
The profile must either prove the evaluated target subtree is unchanged or refuse the
reference context.

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
Array positions in `path` also need a shared type.
Python’s `absolute_path` uses integer indexes.
Ajv’s JSON Pointer uses strings, so TypeScript must decode the pointer against the
validated instance to distinguish an array index `0` from an object key `"0"`. Python
can recover missing required fields from `validator_value` and the instance; parsing the
English message is necessary only for the current `unevaluatedProperties` error surface
and should be protected by a canary test.

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

## softschema PR #42 Evidence

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

### Follow-up evidence for child dependencies

Follow-up probes of the supported subset exposed two additional co-evaluator classes, an
indirect composition-reference class, and one graph-identity case:

| Shape and instance | Raw | Prior PR #44 overlay | Required result |
| --- | --- | --- | --- |
| Structured `items` and structured `contains`; one element carries both field sets | valid | invalid | `child_evaluator_overlap` |
| Literal property and matching pattern apply separate structured schemas to one value | valid | invalid | `child_evaluator_overlap` |
| Two structured matching patterns apply to one value | valid | invalid | `child_evaluator_overlap` |
| `contains` references a definition whose nested object receives inferred closure | valid | invalid | `composition_reference_context` |
| A `oneOf` branch references that kind of definition while a second branch covers the child | invalid | valid | `composition_reference_context` |
| An `allOf` or conditional branch references such a definition while a sibling describes the nested child | valid | invalid | `composition_reference_context` |
| A reference with validation siblings reaches such a definition | valid | invalid | `composition_reference_context` |

Caller-constructed TypeScript and Python schema objects exposed a separate source of
order dependence.
Reusing one mapping object as both a definition and an application site
caused the last graph visit to overwrite location metadata.
Depending on key order, the same schema either closed a reusable definition or left an
application site open.
Portable YAML aliases are already rejected, but the library APIs accept in-memory
objects. Rejecting repeated mapping identity as `shared_subschema` turns that silent
under- or over-enforcement into a deterministic schema error.
TypeScript repeats that identity check before returning a content-addressed
validator-cache hit because identity sharing is not represented in serialized JSON.

## Key Insights

### Enforcement is a new language profile

The authored schema permits additional properties when no closure keyword says
otherwise.
softschema’s enforced mode deliberately assigns a stronger meaning to a subset
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

| Design dimension | Explicit authored closure | Checked validation-time subset | General graph transformer |
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

### Option B: Support only transformations the validator can verify

Keep the validation-time overlay, but analyze the complete resource graph first.
Publish the supported shapes as a normative matrix, apply closure only for those shapes,
and return a stable `enforcement_unsupported` schema error for everything else.

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

The stacked remediation implements Option B. Both runtimes now prepare the root and
supplied resources as one checked offline graph, keep reusable targets open, and close
structured application sites independently.
The implementation covers static pointers, escaped pointer tokens, anchors, nested
definitions, embedded resource identities, supplied resources, literal and pattern
declarations, alternatives, conditionals, dependent schemas, plain array item closure,
and disjoint `prefixItems`/`items` within the profile specified in the main spec.

The implementation also makes the boundary explicit.
Dynamic references and the instance-location, child co-evaluator, and context-sensitive
reference shapes for which static analysis cannot prove safe annotation flow return
`enforcement_unsupported` with a stable reason.
Enforced model-only calls return `enforced_schema_required`. Missing and
undeclared-field errors carry the affected `property`, with one record per field, and
array positions in TypeScript and Python error paths are numeric.
Repeated in-memory schema object identities return `schema_invalid/shared_subschema`.

Shared semantic vectors now compare raw and enforced outcomes across both runtimes,
including reference/resource equivalents and each unsupported reason.
Python and TypeScript agree on verdicts for the support matrix.
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
- [x] Refuse independently closed sibling child evaluators (`ss-tmf7`, `ss-hkei`).
- [x] Reject shared in-memory subschema identity (`ss-juw0`).
- [x] Specify success-sensitive branch declarations (`ss-zylb`).
- [x] Normalize array-index paths and harden Python field recovery (`ss-zpso`,
  `ss-girn`).
- [x] Refuse context-sensitive composition references to transformed targets
  (`ss-2hn1`).

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

- [JSON Schema overview](https://json-schema.org/overview/what-is-jsonschema)
- [JSON Schema glossary](https://json-schema.org/learn/glossary)
- [JSON Schema basics](https://json-schema.org/understanding-json-schema/basics)
- [JSON Schema dialects and `$schema`](https://json-schema.org/understanding-json-schema/reference/schema)
- [JSON Schema object keywords](https://json-schema.org/understanding-json-schema/reference/object)
- [JSON Schema composition](https://json-schema.org/understanding-json-schema/reference/combining)
- [JSON Schema specification timeline](https://json-schema.org/specification-links)
- [Draft 6 release notes](https://json-schema.org/draft-06/json-schema-release-notes)
- [Draft 7 release notes](https://json-schema.org/draft-07/json-schema-release-notes)
- [Draft 2019-09 release notes](https://json-schema.org/draft/2019-09/release-notes)
- [Draft 2020-12 release notes](https://json-schema.org/draft/2020-12/release-notes)
- [JSON Schema Draft 2020-12 Core](https://json-schema.org/draft/2020-12/json-schema-core)
- [Draft 2020-12 annotations](https://json-schema.org/draft/2020-12/json-schema-core#section-7.5)
- [Draft 2020-12 schema references](https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.3)
- [Draft 2020-12 in-place applicators](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2)
- [Draft 2020-12 `allOf`](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.1)
- [Draft 2020-12 `anyOf`](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.2)
- [Draft 2020-12 conditional applicators](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2)
- [Draft 2020-12 `dependentSchemas`](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.4)
- [Draft 2020-12 `contains`](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.3)
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
