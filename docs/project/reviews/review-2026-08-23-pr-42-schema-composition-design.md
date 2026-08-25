---
title: Senior Design Review of PR 42 Composed-Schema Enforcement
description: >-
  Holistic review of softschema's Draft 2020-12 composition, reference,
  undeclared-property enforcement, validation, parity, error, and documentation design
  at PR 42 head 18946cb.
author: Joshua Levy with OpenAI Codex assistance
---
# Senior Design Review: PR #42 Composed-Schema Enforcement

**Date:** 2026-08-23

**PR:**
[#42: Validate composed schemas under enforced instead of refusing them](https://github.com/jlevy/softschema/pull/42)

**Reviewed head:** `18946cb3d161b785df6b0b47779c6cc0366e1bc4`

**Verdict:** Request changes.

## Scope

This is a full design review of the current PR head after the earlier review,
disposition, and follow-up audit.
It does not repeat findings already fixed in `5aa2037` and `fda8fe4`. It examines the
larger contract around:

- Draft 2020-12 object evaluation and composition;
- references, definitions, anchors, dynamic references, and supplied resources;
- the meaning and API reach of `status: enforced`;
- Python `jsonschema` and TypeScript Ajv parity;
- Pydantic and Zod source-model behavior;
- structural error records and their stable match surface;
- shared vectors, semantic test oracles, and issue tracking; and
- the spec, guide, Python design, TypeScript design, development guide, docstrings, and
  active plan.

The supporting research is in
[JSON Schema Composition, Field Dependencies, and Undeclared Properties](../research/research-2026-08-23-json-schema-composition-and-enforcement.md).
It records the normative keyword semantics, runtime comparison, paired probes, design
options, and primary sources behind this review.

In this review, **object closure** means one local rule: at one object instance
location, reject each present property whose value is not evaluated by a successful
applicable schema. It does not mean making an entire schema resource graph strict.

The stack’s central capability is additive: supported `allOf`, conditional, and
dependent-schema object shapes that version 0.6.2 refused can now receive real
validation verdicts.
The complete stack is nevertheless breaking for consumers that relied on old
alternative/reference transformations, permissive supplied-resource preparation, or the
old structural diagnostic record shape.
It does not change `soft` or `permissive` validation, compiled schema bytes, or
`schema_sha256`.

## Executive Assessment

The PR fixes the original `allOf` and conditional cases in the right direction.
`unevaluatedProperties` at the composition root is the correct Draft 2020-12 mechanism;
keeping the overlay validation-only preserves the compiled-schema digest; excluding
`not` from declaration discovery is correct; and the shared Python/TypeScript vectors
are useful.

The problem is the abstraction boundary.
The implementation treats object closure—the rule that rejects each present property
whose value is not evaluated by a successful applicable schema at that object
location—as a recursive syntax-tree rewrite with a root-only `$defs` lookup and a global
open/closed choice for each definition.
The public design describes a semantics-preserving policy over Draft 2020-12 schemas.
Those are not equivalent systems.

Direct probes show all four failure classes:

- **over-narrowing:** raw-valid data with only declared keys becomes invalid;
- **widening:** raw-invalid `oneOf` data becomes valid;
- **under-enforcement:** undeclared keys remain valid; and
- **runtime divergence:** a supplied resource accepted by Python is rejected by Ajv
  because graph-wide portable checks are skipped.

The current code should not become the normative design.
My recommendation is to restore an explicit unsupported result for unproved shapes,
publish an exact `status: enforced` support matrix, and prepare the complete
schema-resource graph before either runtime compiles it.
A general Draft 2020-12 transformer is disproportionate and especially risky in two
implementations.

## Findings

| ID | Severity | Bead | Finding |
| --- | --- | --- | --- |
| R1 | High | `ss-vy4t` | Closing `anyOf` and `oneOf` branches changes union meaning |
| R2 | High | `ss-iq9w` | Reusable-definition closure is global but must be application-site specific |
| R3 | High | `ss-qr8j` | The root is transformed and checked, while the schema resource graph is not |
| R4 | Medium | `ss-w78w` | The declaration model omits `patternProperties` |
| R5 | High | `ss-4est` | `status: enforced` is not an API boundary guarantee |
| R6 | Medium | `ss-5rjo` | Stable structural errors discard the offending property identity |
| R7 | High | `ss-pq0m` | The main documentation does not describe one coherent support contract |

### R1 — Closing alternative branches changes union meaning

**Source:**
[canonicalize.py:57](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/python/src/softschema/canonicalize.py#L57-L67),
[canonicalize.ts:24](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/typescript/src/canonicalize.ts#L24-L36),
[softschema-spec.md:418](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/docs/softschema-spec.md#L418-L425).

The design classifies `anyOf` and `oneOf` branches as complete object descriptions and
injects `additionalProperties: false` into each branch.
Draft 2020-12 makes no such guarantee.
`anyOf` may have several successful branches and must collect annotations from all of
them; `oneOf` validity depends on the number of successful branches.

Both runtimes reproduce these counterexamples:

| Case | Raw schema | Enforced overlay |
| --- | --- | --- |
| `anyOf` branches require and declare `a` or `b`; instance `{a, b}` | valid | invalid |
| overlapping permissive `oneOf` branches declare `a` or `b`; instance `{a}` | invalid | valid |

The first result rejects only declared keys.
The second widens the authored schema by changing branch selection.
That contradicts the PR’s preservation invariant more fundamentally than the already
documented sibling-properties case.

**Required change:** Treat alternatives as in-place composition sites.
Preserve branch selection, leave branches open, and place `unevaluatedProperties` at
their parent when the supported analysis recognizes a structured object declaration.
If the project wants a “disjoint complete record” convention, validate it at schema-load
time. Do not infer it from the presence of `anyOf` or `oneOf`.

### R2 — Definition closure must be application-site specific

**Source:**
[canonicalize.py:224](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/python/src/softschema/canonicalize.py#L224-L287),
[canonicalize.py:326](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/python/src/softschema/canonicalize.py#L326-L336),
[softschema-spec.md:456](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/docs/softschema-spec.md#L456-L480).

The reference-context pass chooses one global state for a definition.
If any reference is standalone, the definition receives lexical
`additionalProperties: false`, including at every composed use.

That makes schema use sites interfere.
A definition used once under `properties` and once in an `allOf` extension rejects the
extension’s sibling field.
The standalone reference can be optional and absent from the tested instance; merely
adding that unused schema path changes the composed verdict.

The same global mutation defeats explicit opt-out:

```yaml
$ref: "#/$defs/Base"
unevaluatedProperties: true
$defs:
  Base:
    type: object
    properties: {street: {type: string}}
```

`{street: s, extra: 1}` is raw-valid and enforced-invalid because `Base` has already
received `additionalProperties: false`. The claim that explicit closure “anywhere always
wins” is therefore false across a reference boundary.

**Required change:** Keep reusable definition roots open unless the author explicitly
closed them. Apply annotation-aware closure at each reference application site that the
profile identifies as a structured object.
This resolves mixed use and lets explicit closure at the referring site retain its
intended scope. Reference chains and cycles need graph-aware analysis; unsupported
topologies should fail explicitly.

### R3 — Prepare the complete schema resource graph

**Source:**
[Python validator construction](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/python/src/softschema/validate.py#L114-L139),
[TypeScript validator construction](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/typescript/src/validate.ts#L176-L195),
[root-only definition map](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/python/src/softschema/canonicalize.py#L224-L232).

Draft 2020-12 references are URI references.
They can target escaped JSON Pointers, plain-name `$anchor`s, nested and embedded
resources whose `$id` changes the base URI, supplied external resources, and dynamic
anchors. The overlay recognizes only raw strings matching direct root `#/$defs/Name` or
`#/definitions/Name` entries.
Listing `$dynamicRef` as a reference keyword does not implement dynamic resolution.

Paired probes show the consequences:

- extensions through `$anchor` and nested `$defs` are raw-valid and enforced-invalid;
- a root reference to a supplied external object remains open under enforced, so an
  undeclared key passes; and
- resources bypass the portable regular-expression check.
  An external resource using `(?P<x>a)` built and validated in Python, while Ajv
  returned `schema_invalid`.

The last result reopens a parity defect the resource API was designed to prevent.
The same concern applies to metaschema validation and any future graph-level check.

**Required change:** Introduce one `prepare_schema_graph(root, resources, policy)` stage
in each implementation.
It should validate portable values and patterns, validate every resource schema, index
identities and reference targets using URI semantics, analyze the enforced profile,
transform every in-scope resource, and only then compile the validator.
Keep retrieval disabled.
If anchors or dynamic scope are outside the overlay profile, return a stable
unsupported/schema error rather than a wrong document verdict.

### R4 — `patternProperties` is missing from the declaration model

**Source:**
[composed-reference classification](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/python/src/softschema/canonicalize.py#L257-L262),
[declaration scan](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/python/src/softschema/canonicalize.py#L359-L382),
[spec rule 2](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/docs/softschema-spec.md#L438-L446).

Draft 2020-12 explicitly includes `patternProperties` annotations in the evaluated set
consumed by `unevaluatedProperties`. The current scan recognizes only `properties`.

Two opposite failures follow:

- A pattern-only object with `{x_ok: v, bogus: 1}` remains valid under enforced; the
  unmatched key is never closed out.
- A `$ref` with sibling `patternProperties: {"^x_": ...}` rejects `x_ok` because the
  referenced definition closes lexically and cannot see the sibling pattern annotation.

Calling every object without `properties` a free-form mapping is therefore inaccurate.
A pattern map is structured even when it has no literal property declarations.

**Required change:** Define the policy in terms of evaluation-producing keywords, not a
single syntactic keyword.
Include nonempty `patternProperties` in direct declaration, fragment discovery, and
reference-site classification.
Add simple, composed, reference-sibling, and overlapping-pattern outcome vectors.
State explicitly that `required`, `dependentRequired`, and `propertyNames` do not
evaluate property values.

### R5 — `status: enforced` is not an API boundary guarantee

**Source:**
[Python `validate_values`](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/python/src/softschema/validate.py#L335-L355),
[model-only artifact path](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/python/src/softschema/validate.py#L695-L716),
[TypeScript `validateValues`](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/typescript/src/validate.ts#L397-L410),
[documented Python example](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/docs/softschema-python-design.md#L158-L184).

The design says an enforced contract is authoritative at the boundary.
The API makes the structural schema optional.
With only a model, structural validation is skipped as `inferred_via_model`; Pydantic’s
default ignores extras, and a normal Zod object strips them.

Using the documented model-only Python contract shape, `{known: 1, bogus: 2}` returned
an overall valid enforced result.
The low-level `validate_values` and `validateValues` helpers also accept a schema but
expose no status or strict-extras option, so a caller cannot request the documented
enforced policy there.

**Required change:** Choose one contract and document it consistently:

1. require a compiled/derived structural schema for `status: enforced`;
2. derive the structural schema from the model in memory and apply the same graph
   pipeline; or
3. define and implement strict semantic-model behavior in both runtimes.

The first or second option best preserves a language-neutral boundary.
At minimum, add strict options to both values APIs and fix the model-only design
example.

### R6 — Structural errors lose the offending field identity

**Source:**
[Python error records](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/python/src/softschema/errors.py#L144-L213),
[Ajv normalization and collapse](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/packages/typescript/src/errors.ts#L228-L272),
[documented match surface](https://github.com/jlevy/softschema/blob/18946cb3d161b785df6b0b47779c6cc0366e1bc4/docs/softschema-spec.md#L618-L632).

The new `code` category is useful, but `{kind, code, path}` is not enough to identify a
field-level repair. For `required: [a, b]` and `{}`, Python emits two records whose
normalized `kind`, `code`, `path`, message, and `validator_value` are identical.
The message says `required property ['a', 'b'] is missing` twice.
Undeclared-property records similarly collapse all keys at an object path to a generic
message.

Both native engines already provide the missing detail: Python’s native message names
the missing or extra keys, and Ajv exposes `params.missingProperty`,
`params.additionalProperty`, or `params.unevaluatedProperty`.

**Required change:** Add a stable `property` or sorted `properties` detail field before
normalizing multiplicity.
Match repairs on `{kind, code, path, property}`. Keep `validator_value` and the full
instance diagnostic-only.
This is a public record-shape change and should be documented and covered by the shared
vectors.

### R7 — The documentation does not define one coherent contract

The main spec is admirably detailed, but several statements cannot all be true:

- The invariant says enforced rejects nothing except genuinely undeclared keys, while
  rule 4 explicitly accepts a mixed-reference “residual” that rejects a declared key.
- The alternatives table says validation picks one `anyOf` branch; Draft 2020-12 allows
  several successful branches and requires collecting all of their annotations.
- The spec says explicit closure anywhere always wins, but a referenced target’s
  injected closure defeats an explicit `unevaluatedProperties: true` at the referring
  site.
- “What enforced does not close” lists two shapes, but pattern-only schemas and external
  resources are additional silent gaps.
- The suggested `$defs`/`$ref` workaround for an object nested below a fragment does not
  work when that is the definition’s only reference.
  The context pass classifies the ref as composed and leaves the target open; paired
  probes accepted the nested extra key.

The surrounding design docs also drift:

- The TypeScript design says structural error records are identical and match Python for
  every keyword, while the committed `engine_deviations` vectors intentionally pin
  different record sets.
- The Python design omits the new `code` field from the documented record shape.
- The Python validator docstring still describes only `additionalProperties` injection.
- The guide says a conditional `required` error names the forgotten field; a multi-key
  required array produces indistinguishable normalized records.
- `ss-p32o` is named in the active plan and vector comments, but `tbd show ss-p32o`
  returns “Issue not found” on the reviewed head.

**Required change:** After resolving R1-R5, make the spec contain one normative support
matrix: declaration keywords, in-place applicators, reference forms, resource handling,
explicit precedence, unsupported shapes, and the schema requirement for enforced status.
Have both design docs and code docstrings link to it.
Document verdict parity separately from error-record-set parity.
Verify every workaround with an end-to-end vector and every issue link with `tbd show`.

## Recommended Design

The near-term design should support a documented subset whose transformations the
validator checks before use, not attempt an unrestricted transformer.

1. **Prepare the graph.** Parse and validate the root plus every supplied resource,
   index URI identities and targets, and keep the registry offline.
2. **Analyze support.** Classify instance-site declarations and in-place composition for
   the explicitly supported keyword/reference subset.
3. **Transform at sites.** Preserve reusable definitions; apply `additionalProperties`
   only to self-contained lexical objects and `unevaluatedProperties` where annotations
   meet.
4. **Fail honestly.** Return a stable unsupported/schema result when safe placement
   cannot be proved, including unresolved dynamic or custom applicator behavior.
5. **Compile once.** Give the prepared graph to Python `jsonschema` or Ajv and cache
   only after all graph checks pass.

Longer term, prefer explicit closure in compiled schemas.
That makes the schema itself the portable boundary contract and puts the effective
behavior under `schema_sha256`. The tradeoff is that promoting status requires model
configuration and regeneration, which is simpler than maintaining a second JSON Schema
compiler indefinitely.

## Test Strategy

The current unit tests emphasize transformed keyword shape.
Make raw-versus-enforced document outcomes the primary oracle.

For every supported shape, require:

- raw-invalid implies enforced-invalid;
- raw-valid remains enforced-valid when every present key is evaluated by the declared
  policy; and
- adding a single unmatched key changes only the enforced verdict.

Add metamorphic pairs for inline versus `$ref`, pointer versus anchor versus external
resource, one reference versus an unused second reference, literal versus pattern
properties, and root versus nested composition.
Run the same vectors through Python and TypeScript.
Keep transform-shape assertions only as secondary tests.

## Non-Blocking Suggestions

- Move `apply_enforced_extras` out of the canonicalization module even before the full
  graph pipeline lands.
  A validation-only policy transform has different inputs, invariants, and failure modes
  from canonical schema normalization.
- Vendor or pin the relevant official JSON Schema Test Suite cases for the declared
  profile. The local metamorphic vectors should cover softschema policy; the official
  cases should cover runtime vocabulary and reference conformance.
- Give the enforced profile a machine-readable version or capability report if it grows.
  That lets hosts reject unsupported schemas before validating a document and makes a
  future profile expansion an explicit compatibility event.

## Prior Review and False Positives

The earlier review correctly found the first `$ref` extension, `not`, nested-fragment,
and nested-alternative failures.
The current head fixes or documents those exact probes.
This review’s findings come from broader equivalent and mixed-use shapes, not a rerun of
the resolved list.

The following behavior checked out:

- the PR’s central two-branch `allOf` and conditional cases validate correctly;
- root composition uses annotation-aware closure in both runtimes;
- simple explicit closure on the same schema node remains unchanged;
- `not` is correctly excluded from declaration discovery;
- compiled schema content and digest remain untouched by the overlay; and
- Python and TypeScript mirror the current transformation, so most failures above are
  shared semantic defects rather than port drift.

## Validation Status

- Local Python suite: 189 passed.
- Local TypeScript suite: 188 passed.
- Local golden corpus: 49 Python, 47 Node, and 49 Bun cases passed; the
  cross-implementation diff passed.
- Local lint, formatting, types, codespell, and documentation-footer checks: passed.
- PR diff whitespace check: passed.
- GitHub CI: all 18 checks green at the reviewed head.
- Additional paired probes: 13 schema shapes plus native error-detail and external
  resource regex probes.

Green CI confirms the implementation matches its current corpus.
The counterexamples show that the corpus does not yet prove the stated design invariant.

## Merge Guidance

R1-R3 and R7 should block the current design from becoming normative.
R4-R6 can be sequenced as tracked follow-up work only if the public contract is narrowed
immediately and the open beads remain attached to the review epic.
No code changes are proposed by this review.

## Status Addendum — 2026-08-23

The stacked remediation implements the support-matrix recommendation in commit
`9d69517`. The original findings above remain as the historical review of PR #42 at
`18946cb`; this addendum records their disposition after implementation and document
reconciliation.

| ID | Disposition | Resolution |
| --- | --- | --- |
| R1 | Fixed | Alternatives remain unchanged internally and close at their parent, preserving `anyOf` annotations and `oneOf` branch selection. |
| R2 | Fixed | Reusable definitions and resources remain open; each supported structured `$ref` application site receives its own undeclared-property rule. |
| R3 | Fixed | Both runtimes check, index, transform, and compile the root and supplied resources as one offline graph. |
| R4 | Fixed | Nonempty `patternProperties` participates in declaration analysis and graph-wide portable regex checks. |
| R5 | Fixed | Enforced artifact and values APIs require a structural schema; both values APIs expose status and resources. |
| R6 | Fixed | Missing and undeclared-field errors carry `property`, with one record per affected field. |
| R7 | Fixed | The spec now owns one normative support matrix; the guide, implementation designs, development process, changelog, completed plan, and code agree with it. |

The remediation restores a narrow, structured `enforcement_unsupported` result instead
of claiming support for unproved topologies.
Each reason has an author action in the spec.
Shared semantic vectors cover supported graph equivalents and unsupported boundaries in
Python and TypeScript; transformation-shape tests are secondary.

The first non-blocking suggestion was adopted by moving the overlay from canonical
schema normalization into dedicated `enforcement` modules.
Vendoring the official JSON Schema Test Suite remains deferred: the checked policy
vectors cover softschema’s language boundary, while the existing runtime suites and
metaschema checks cover the current supported vocabulary.
A machine-readable profile version is also deferred until the support matrix grows
enough to require capability negotiation.

Follow-up local validation passed 192 Python tests and 190 TypeScript tests, the 49
Python, 47 Node, and 49 Bun golden journeys, both package builds, publint, lint, type
checks, and the direct Python/TypeScript parity diff.

**Final verdict:** Approved.
All required findings are addressed in the stacked remediation; final GitHub CI evidence
is recorded on the pull request.

## Follow-up Review Addendum — 2026-08-24

A second holistic review of the updated PR #42 to PR #44 stack found seven gaps in the
support-matrix remediation.
The
[published review](https://github.com/jlevy/softschema/pull/44#issuecomment-5397960201)
covered child applicators, shared graph identity, success-sensitive declarations, error
parity, and release hygiene.
The mandatory pre-commit review then found an eighth class: references can carry
globally inferred closure into a context where another schema controls intersection,
selection, matching, prohibition, or conditional success.

**Verdict at follow-up review:** Request changes.

| ID | Severity | Bead | Disposition | Resolution |
| --- | --- | --- | --- | --- |
| S1 | High | `ss-tmf7` | Fixed | `contains` remains an unchanged matcher; structured `items` or `prefixItems` co-evaluation is refused when inferred closure could change the element result. Plain `items` and disjoint `prefixItems`/`items` remain supported. |
| S2 | High | `ss-hkei` | Fixed | Matching literal and pattern value schemas, and conservatively every structured pattern pair, return `child_evaluator_overlap` when either evaluated subtree would receive inferred closure. |
| S3 | Medium | `ss-juw0` | Fixed | Repeated in-memory schema mapping identity returns `schema_invalid/shared_subschema`. TypeScript repeats graph preparation before returning a content-cache hit, so identical JSON content cannot bypass the identity check. |
| S4 | Medium | `ss-zylb` | Fixed | The invariant and rules now depend on successful property evaluation. Conditional and dependent branch declarations are admitted only when the branch applies and succeeds. |
| S5 | Medium | `ss-zpso` | Fixed | TypeScript decodes Ajv pointers against the instance, producing numeric array indexes without changing numeric-looking object keys. |
| S6 | Low | `ss-girn` | Fixed | Python derives missing required properties from validator data. The unavoidable `unevaluatedProperties` message parser has canary coverage for multiple and parenthesized keys. |
| S7 | Low | `ss-9pjf` | Fixed | Stack wording, the resolved alternatives bead, values-API status/resource options, and root self-reference guidance are reconciled. A later compatibility gate preserved the released model-only results. |
| S8 | High | `ss-2hn1` | Fixed | A `$ref` under context-sensitive composition, or beside validation siblings, is refused as `composition_reference_context` when its evaluated target subtree would receive inferred closure. Pure application sites remain supported. |

### Design assessment

The documented-subset architecture remains the right near-term choice.
A general Draft 2020-12 transformer would need instance-location analysis across
arbitrary vocabularies and dynamic scope in two runtimes.
The implementation instead supports a documented subset and returns one stable,
actionable refusal when it cannot prove that inferred closure preserves the authored
evaluation graph.

The follow-up changes make that boundary systematic.
Post-transform graph analysis records every inferred closure and then checks both
sibling child evaluators and context-sensitive references against the evaluated target
subtree. This is more conservative than attempting regex-disjointness or reference-path
equivalence, but it does not silently change a document verdict.
Authors can cross the boundary by making closure explicit at the affected structured
descendants or by separating the co-evaluating schemas.

### Documentation

The main spec owns the successful-evaluation invariant, exact pure-reference sibling
set, array and child-applicator matrix, refusal reasons, shared-identity requirement,
and author actions. The guide summarizes ordinary author behavior.
Both implementation designs document runtime-specific error recovery and caching.
The research brief records the counterexamples, the Python/TypeScript behavior, and the
primary Draft 2020-12 sources.

### Follow-up validation

- Python: 194 tests and 49 golden journeys passed.
- TypeScript: 192 tests passed with at least 98% line coverage; 47 Node and 49 Bun
  golden journeys passed.
- Lint, formatting, types, documentation footers, both package builds, publint, and the
  direct cross-runtime parity diff passed.

**Final follow-up verdict:** Approved.
The review findings and the additional pre-commit finding are addressed in the stacked
remediation. Final GitHub CI evidence is recorded on PR #44.

## Pre-Merge Compatibility Gate — 2026-08-24

The final gate compared the complete stack with released version 0.6.2 and exercised the
actual trading-models, GTIA v2, and metaproc consumers.
It found two release blockers before the compatibility fixes:

1. Model-only contracts marked `enforced` changed from native semantic validation to
   `enforced_schema_required`. This broke metaproc’s registered Pydantic contracts.
2. A common generated nullable model field, `anyOf: [{$ref: ...}, {type: "null"}]`,
   returned `composition_reference_context` even when every referenced object already
   stated its unknown-property policy.
   This broke valid GTIA query-context and cohort artifacts.

Both are fixed. Model-only and metadata-only paths retain their 0.6.2 verdicts and skip
reasons. A pure `$ref` to a target that already states `additionalProperties` or
`unevaluatedProperties` receives no redundant wrapper closure.
References to implicitly open targets, references with validation siblings, and target
subtrees that still need inferred closure retain the checked safety analysis.

### Compatibility Results

| Surface | Evidence | Result |
| --- | --- | --- |
| Ordinary structural verdicts | A 30-case 0.6.2-versus-stack matrix covered flat objects, required fields, explicit open and closed objects, inline nesting, arrays, local `$defs`/`$ref`, pattern properties, free-form maps, scalar constraints, nullability, and raw versus enforced status | Every pre-existing accept/reject verdict matched. The only matrix difference is the new optional `status` parameter on the values API. |
| Model-only and metadata-only calls | Direct artifact and values probes plus metaproc’s registered contracts | Verdicts and structural skip reasons match 0.6.2. Native Pydantic or Zod validation still runs. |
| Generated trading and GTIA schemas | 44 compiled sidecars containing 377 structured object schemas, 429 references, and 536 `anyOf` sites | All 377 object schemas already state their property policy: 249 use `additionalProperties: false` and 128 use `additionalProperties: true`. The enforced overlay does not need to infer simple-object closure there. |
| Trading models | Full `packages/trading-models` suite against the stack | 102 passed. |
| GTIA v2 | Full test directory against the stack | 1,547 passed. One stale assertion for a pure-YAML CLI limitation already removed in 0.6.2 was excluded. |
| metaproc | Full vendored suite against the stack | 4,270 passed and 8 skipped. |
| softschema Python | Lint, types, unit/integration tests, package build, and goldens | 194 tests and 49 golden journeys passed; sdist and wheel built. |
| softschema TypeScript | Lint, types, coverage tests, package build, publint, and Node/Bun goldens | 192 tests passed at 98.02% line coverage; 47 Node and 49 Bun golden journeys passed. |
| Cross-runtime behavior | Direct Python-versus-Node CLI comparison | All representative commands matched semantically. |
| Compiled output | Compiler code-path review and conformance tests | Canonical schema bytes and `schema_sha256` remain unchanged. |

### Client Impact That Remains

The stack is validity-compatible for ordinary schema-backed use, but it is not fully
output-compatible:

- Structural violations add stable `code` and field-level `property` values.
  Missing or undeclared fields produce one record per affected property.
  A referenced object may report the mechanism as `unevaluatedProperties` instead of
  `additionalProperties`. Consumers should match `code == "undeclared_property"` and
  include `property`, rather than match the engine keyword or assume one aggregate
  record.
- Callers using the low-level external `resources` option must use absolute URI keys
  without fragments, and a resource root `$id` must resolve to its key.
  Ordinary callers that pass only a compiled schema are unaffected.
- `validate_values` and `validateValues` gain optional `status` and `resources`
  arguments. Existing calls keep their behavior.
- The supported package-root exports are unchanged.
  A deep import of `EnforcementUnsupportedError` from a canonicalization module was
  internal and is not retained as a public compatibility surface.

Because diagnostic records and supplied-resource inputs remain breaking surfaces, this
stack should release as version 0.7.0, not 0.6.3. Existing consumers constrained to
`softschema>=0.6,<0.7` will not receive those output changes automatically.

**Final compatibility verdict:** Approved for merge and for a 0.7.0 release.
No known ordinary-schema or current trading/GTIA validity regression remains.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
