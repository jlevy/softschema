# softschema Spec

softschema is a file convention for Markdown/YAML artifacts that are readable by humans
and structured enough for tools.
The spec is programming-language agnostic.
This repository ships two interchangeable implementations of the spec, a Python/Pydantic
package and a TypeScript/Zod package, held to the same portable behavior.

For the adoption guide, examples, and tutorials, see
[softschema Guide](softschema-guide.md).
This document defines what an artifact must look like and how a validator must treat it.

## Scope

This spec defines the artifact format, the recognized metadata, and the validation
expectations a conforming implementation must honor.
It does not define how to author artifacts, how to migrate existing documents, or how a
specific implementation should package itself.

## Conformance Language

The words “must” and “must not” state requirements on conforming implementations and
artifacts; “may” marks optional behavior.
A document that meets every “must” is a conforming artifact, and a tool that honors
every “must” is a conforming implementation.
This spec uses plain “must” rather than the capitalized RFC 2119 forms.

(“softschema”, lowercase, names this package, CLI, and spec; “soft schema(s)”, two
words, names the general practice.
The lowercase brand stays lowercase even at the start of a Title Case heading.)

## Terminology

These terms are used throughout; each is defined here before it appears in a rule.

| Term | Meaning |
| --- | --- |
| **artifact** | A single conforming file: Markdown with YAML frontmatter, or pure YAML. |
| **frontmatter** | The YAML block delimited by `---` at the top of a Markdown file. |
| **body** | The Markdown after the frontmatter. Reader-facing; never a source of structured values. |
| **metadata block** | The `softschema:` mapping in the frontmatter (or at the document root for pure YAML). It holds softschema’s own keys, not payload data. |
| **payload** | The structured values a consumer reads, validated against a contract. |
| **envelope** | The single top-level key whose value is the payload; the **envelope key** is its name (for example `movie:`). |
| **contract** | The named payload contract—*what* the payload is. |
| **contract ID** | The string that names the contract (for example `example.movies:MoviePage/v1`). |
| **model** | A Pydantic class or Zod schema: a language-specific *source* for a contract. |
| **compiled schema** | The JSON Schema (written as YAML or JSON) that a model compiles to; the language-neutral form of the contract. |
| **profile** | Which artifact shape is in use: `frontmatter-md` or `pure-yaml`. |
| **status** | The boundary maturity of the contract: `soft`, `permissive`, or `enforced`. |
| **generated section** | A block of Markdown body regenerated from a compiled schema, fenced by `softschema:generated` markers. |

Annotated, the parts fit together like this:

```markdown
---
softschema:                          # the metadata block
  contract: example.movies:MoviePage/v1   # the contract ID
  schema: movie-page.schema.yaml          # optional pointer to the compiled schema
  envelope: movie                         # optional declared envelope key
  status: enforced                        # the status
movie:                               # the envelope key
  title: Spirited Away               # ── the payload ──
  release_year: 2001                 #
---
# Spirited Away (2001)              # ── the body (reader-facing) ──
```

## Artifact Profiles

A conforming artifact uses one of two profiles:

| Profile | Description |
| --- | --- |
| `frontmatter-md` | Markdown file with YAML frontmatter. The frontmatter carries the payload; the body is reader-facing prose. |
| `pure-yaml` | YAML file with no Markdown body. The whole document is the payload. |

The `frontmatter-md` profile is the primary shape, and the rest of this spec is written
for it; “frontmatter” there means “the document root” for a `pure-yaml` artifact.

A `pure-yaml` artifact follows the same metadata rules:

- A `softschema:` block at the document root is the metadata block, never payload.
- With an explicit envelope designation, the named key nests the payload.
- Otherwise the whole document root (minus the `softschema` block) is the payload.
- Single-key envelope inference and multi-key ambiguity rejection (below) do **not**
  apply, because the profile’s purpose is “the whole document is the payload.”

```yaml
softschema:
  contract: mycorp.runs:BacktestReport/v1
run_id: run-2026-04-12T18-03-00Z
summary: regression vs baseline
```

The profile is not declared in the metadata block; it is a property of the artifact’s
shape, which an implementation resolves from the artifact itself.
A caller may designate it explicitly (the `--profile` flag, or the profile argument of a
library call). Otherwise an implementation must resolve it as:

1. A `*.yaml` or `*.yml` file name means `pure-yaml`. The name is checked before the
   frontmatter fence, because a YAML document may open with the `---` document-start
   marker that would otherwise scan as the start of a fence.
2. A document with a frontmatter fence is `frontmatter-md`.
3. A fenceless document whose whole text parses to a mapping carrying a root
   `softschema:` block is `pure-yaml`.
4. Anything else is `frontmatter-md`.

Requiring the metadata block in step 3 is what separates a pure-yaml artifact from prose
that happens to parse as YAML: a Markdown document without frontmatter stays
`frontmatter-md` and is rejected for having none.

## Portable YAML Values

YAML is decoded into the JSON-compatible value domain: null, booleans, strings, finite
numbers, lists, and string-keyed mappings.
Integer literals must be within the IEEE-754 safe range (`abs < 2^53`). Negative zero,
duplicate keys, aliases, anchors, merge keys, explicit tags, non-string keys, lone
surrogates, and non-finite numbers are rejected.

Date- and timestamp-shaped plain scalars without an explicit tag decode as strings.
A conforming implementation must preserve the decoded scalar content rather than
construct or canonicalize a host-language date or timestamp value.
Quoted and unquoted date-shaped scalars with the same content therefore produce the same
string.
Portable YAML decoding does not determine whether that string is a valid calendar
date or timestamp; a semantic model or explicit structural assertion may impose that
constraint. An explicit tag such as `!!timestamp` remains unsupported under the
explicit-tag rule.

One YAML document has at most 64 simultaneously open collections, including the root.
Exceeding that depth is `yaml_limit`, as is a host YAML parser stack overflow.
The depth rule is a portability rule rather than a resource ceiling: left to the host,
the two runtimes disagree by an order of magnitude about how deep a document may be, so
a fixed bound is what makes depth mean the same thing in both.

Input size, scalar size, and node count are not bounded.
Those ceilings only answered whether a hostile document could exhaust the parser, and
softschema reads artifacts its own callers just wrote; a cap that can only fire after
the artifact is written destroys completed work rather than rejecting bad input.

These rules bind when an implementation decodes an artifact.
An implementation may let a caller supply a document root it already decoded, so the
artifact is not parsed twice; such a root is trusted as-is and is not re-checked against
these rules.
An implementation that offers this must also publish the readers that decode
a document under them, so “parse it yourself” does not mean “lose the guarantees”: a
root decoded by a host YAML library directly may validate in one implementation and be
rejected by another reading the same file.

For `frontmatter-md`, the opening and closing delimiters begin at column one and contain
`---` plus optional trailing whitespace.
An indented `---` is YAML content, so a block scalar may contain it without ending
frontmatter.

## Frontmatter Artifact Shape

A genuine artifact (a trimmed `examples/movie_page/spirited-away.md`):

```markdown
---
title: Spirited Away (2001)
softschema:
  contract: example.movies:MoviePage/v1
  schema: movie-page.schema.yaml
  envelope: movie
  status: enforced
movie:
  title: Spirited Away
  release_year: 2001
  runtime_minutes: 125
  mpaa_rating: PG
  directors:
    - Hayao Miyazaki
  genres: [Animation, Adventure, Family]
  ratings:
    imdb:
      score: 8.6
      total_votes: 850000
---
# Spirited Away (2001)

*Spirited Away* is Hayao Miyazaki’s animated fantasy about ten-year-old Chihiro, who
slips into a spirit world and takes a job in a bathhouse for the gods to free her parents.
It won the 2003 Academy Award for Best Animated Feature.

## Movie Details

| Field | Value |
| --- | --- |
| Release year | 2001 |
| Runtime | 125 minutes |
| Director | Hayao Miyazaki |
```

The YAML frontmatter is the only authoritative source of structured values.
The body normally **overlaps** with the YAML, and how much is situational: here the
prose adds the Academy Award (which no field carries) and the Movie Details table
restates a few YAML values for the reader.
A conforming consumer reads the YAML and must not parse body prose or tables as a source
of structured values.
(Introductory examples carry no generated sections; those are an optional advanced
feature, defined below.)

## Metadata

The `softschema` mapping is the recognized metadata block:

```yaml
softschema:
  contract: example.movies:MoviePage/v1
  schema: movie-page.schema.yaml
  envelope: movie
  status: enforced
```

| Field | Required | Meaning |
| --- | --- | --- |
| `contract` | yes for self-describing documents | The contract ID (a stable name for the payload contract). |
| `schema` | no (recommended for self-validating documents) | A pointer to the compiled schema. |
| `envelope` | no (recommended when other top-level keys exist) | The declared envelope key. |
| `status` | no | Boundary maturity: `soft`, `permissive`, or `enforced`. |

A `softschema` block with unknown keys, an unknown `status`, a malformed `contract` (see
Contract IDs), or a `schema` or `envelope` that is present but not a non-empty string is
a validation error.

The four keys make an artifact fully self-describing: `contract` names *what* the
contract is, `schema` says *where* its compiled schema lives, `envelope` says *which*
top-level key carries the payload, and `status` says *how strictly* to validate.
`schema` is optional because many hosts resolve the schema out of band (a registry, a
build step, a project convention) and reference the contract only by its ID; such an
artifact carries `contract` alone and is fully conforming.
`envelope` is optional because a single-payload-key artifact needs no designation, and a
caller can always designate one.
See Compiled Schemas for how `schema` is resolved and Envelope Selection for how
`envelope` is applied.

## Envelope Selection

An artifact carries a designated top-level payload key beside `softschema`. That key is
the envelope, and its value is the payload validated against the contract.

Frontmatter may carry any number of additional non-`softschema` top-level keys (for
example `title`, `description`, `tags`, or any other host-specific metadata).
softschema does not interpret them: only the `softschema` block and the designated
envelope key are softschema’s concern.
This lets a softschema artifact coexist with other frontmatter conventions (static-site
generators, doc indexers, custom metadata) without conflict.

The envelope is designated through this precedence (highest first):

1. An explicit caller designation: the `--envelope` flag, or the envelope argument of a
   library call.
2. A host registry binding (a registered contract’s envelope key; library path only).
3. The document’s own `softschema.envelope` declaration.
4. Single-key inference: when exactly one non-`softschema` top-level key exists, it is
   the envelope by convention (no designation required).

Host-controlled designation outranks the document’s declaration for the same reason as
schema resolution (see Compiled Schemas): a document must not silently re-point a host’s
validation. In a CLI run with no registry, the chain is `--envelope` >
`softschema.envelope` > inference.

An implementation must:

- Apply the precedence above.
  When multiple non-`softschema` keys exist and nothing above designates the envelope,
  reject the document as ambiguous; auto-detection is intentionally not extended to
  multi-key documents.
- Reject documents that lack the designated envelope key, or that have zero
  non-`softschema` keys when an envelope is required.

For example, the movie artifact above carries both `title:` and `movie:`. With two
non-`softschema` keys, inference does not apply, so the artifact declares
`envelope: movie` in its metadata block—`title:` stays an uninterpreted host key, and
the artifact validates with no flags.
A caller can still override with `--envelope` on a given run.

## Contract IDs

A contract ID names a payload contract.
Its **shape** is enforced; its **style** is advisory.

Enforced grammar:

```text
contract-id = [ namespace ":" ] name [ "/" version ]
namespace   = segment *( "." segment )      ; segment = [a-z0-9_]+
name        = [A-Za-z_][A-Za-z0-9_]*
version     = [A-Za-z0-9_.-]+
```

No whitespace; at most one `:`; at most one `/`; no empty segments.
A `contract` value that violates the grammar is a malformed `contract` (rejected at
metadata-parse time, independent of `status`).

Advisory (recommended, never enforced): an UpperCamelCase `name`, a reverse-DNS or short
product-tag `namespace`, and short versions (`v1`, `1.0`). Examples:

- `example.movies:MoviePage/v1`
- `example.docs:IncidentReview/v1`
- `com.acme.docs:IncidentReview/1.0`

A contract ID may correspond to a Pydantic class, a Zod export, a precompiled JSON
Schema, a database record, or a hand-authored validator—all equally valid.
It is not required to be an import path or a class name.

## Status Values

| Status | Meaning |
| --- | --- |
| `soft` | A convention exists, but no boundary schema is enforced. |
| `permissive` | Known fields validate; extension fields may be allowed by the source model. |
| `enforced` | The schema is authoritative at the boundary. |

`status` records intended maturity, and `enforced` tightens validation:

- `soft` and `permissive` do not change validation behavior; whether a model allows
  extra fields is configured on the source model.
- `enforced` makes the schema authoritative at the boundary: a conforming validator
  treats an object schema that declares properties but omits closure as closed.
  Which keyword closes it depends on whether the schema composes constraints (see
  below). An explicit `additionalProperties` or `unevaluatedProperties` value in the
  schema (true, false, or a subschema) always wins, so a schema can opt specific objects
  out of strictness. Object schemas that declare no properties anywhere (free-form
  mappings) are unaffected.
  The overlay applies at validation time only; it never changes the compiled schema.

### Closure under `enforced`

Closure is the rule that turns `enforced` from an intention into a check.
It is worth deriving rather than memorizing, because the obvious implementation is wrong
for any schema that composes constraints, and the reason is not obvious.

#### The invariant

Closure must satisfy two conditions at once:

1. **Reject undeclared keys.** A key the schema names nowhere is an authoring bug.
2. **Reject nothing else.** A document the author’s own schema accepts must stay valid
   when `enforced` is switched on.
   Closure adds a check; it does not change the contract.

Condition 2 is the one that constrains the design.
Everything below follows from asking, precisely, what “the schema names this key” means.

#### Why the lexical answer works, until it doesn’t

`additionalProperties` answers “is this key declared?”
by consulting the `properties` of **the same schema object it appears in** — nothing
else. Call this the lexical answer.

For a schema that declares everything in one place, the lexical answer is exactly right:

```yaml
type: object
properties: {name: {type: string}}
additionalProperties: false      # sees `name`; rejects everything else
```

Now compose.
In JSON Schema, an *in-place applicator* is a keyword whose subschemas apply
to **the same instance location** as the parent — `allOf`, `anyOf`, `oneOf`, `not`,
`if`/`then`/`else`, `dependentSchemas`, and `$ref`. (Contrast a *child* applicator like
`properties` or `items`, whose subschemas apply to a child location.)
In-place applicators mean a single instance location can be described by several schema
objects at once:

```yaml
type: object
properties: {a: {type: string}}
allOf:
  - properties: {b: {type: string}}
additionalProperties: false      # sees only `a`
```

`{"a": "x", "b": "y"}` satisfies the author’s schema — `b` is declared, one applicator
over — and `additionalProperties` rejects it.
Condition 2 is violated.
The lexical answer was never a definition of “declared”; it was a shortcut that happens
to coincide with the definition when all declarations sit in one object.

#### The annotation answer

2020-12 provides the non-lexical answer.
When a subschema validates **successfully**, its `properties` keyword produces an
*annotation* naming the keys it matched, and annotations from in-place applicators
propagate to the schema object containing them.
`unevaluatedProperties` consults those collected annotations instead of its lexical
siblings:

```yaml
type: object
properties: {a: {type: string}}
allOf:
  - properties: {b: {type: string}}
unevaluatedProperties: false     # sees `a` and `b`
```

`{"a": "x", "b": "y"}` now passes, and `{"a": "x", "zzz": 1}` is still rejected.
Both conditions hold.

Two properties of the annotation model drive every rule that follows:

- **Annotations propagate upward to the composition root, not sideways.** A branch
  cannot see its siblings’ annotations.
  So the closure keyword must be placed at the object where the applicators meet — not
  inside any of them.
- **Only successful subschemas contribute.** A failing branch, a `not` whose subschema
  failed, or an `if` whose condition was false all contribute nothing.

#### Which subschemas may be closed on their own

Given the above, a subschema can carry its own closure only if it is a **complete
description** of its instance location — if nothing else contributes declarations there.
Sorting the in-place applicators by that question:

| Kind | Keywords | Is a branch a complete description? | Treatment |
| --- | --- | --- | --- |
| Alternatives | `anyOf`, `oneOf` | By convention yes — validation picks one branch, and the compiled shape of an optional field is `anyOf: [{$ref: …}, {"type": "null"}]` | Closed on its own terms |
| Fragments | `allOf`, `if`, `then`, `else`, `not`, `dependentSchemas` | No — each contributes *part* of the constraints, and `if` contributes a *matcher* rather than a declaration | Never closed internally; the composition root closes instead |

The alternatives row rests on an authoring convention, not a guarantee the spec makes: a
node that declares `properties` *and* carries alternatives that declare more breaks it.
That shape is a known defect rather than a supported one — see the tracked issues.

#### The rules

Four rules implement the invariant.
Each is a direct consequence of the two annotation properties above.

1. **Never inject closure inside a fragment subtree.** Annotations do not travel
   sideways, so a fragment cannot see what its siblings declare; closing it lexically
   re-creates the failure in “Why the lexical answer works, until it doesn’t”. Closing
   an `if` matcher is worse than wrong: it changes which documents the condition
   matches, so the conditional silently stops firing instead of failing loudly.

2. **A node declares properties if it carries `properties`, or if a fragment applicator
   under it does.** The second half matters because a schema may declare every property
   inside its `allOf` branches and nothing at the root; without it, such a schema would
   be enforced nowhere.
   The scan recurses through fragment applicators and follows local `$ref` targets, and
   stops there — alternatives are not traversed, and `not` is excluded, since the
   properties under it name what must be *absent*. Counting a prohibition as a
   declaration would close the schema over keys that can never be evaluated, admitting
   nothing at all.

3. **Close such a node with `unevaluatedProperties: false` when it carries a fragment
   applicator or a reference keyword, and `additionalProperties: false` otherwise.**
   `$ref` and `$dynamicRef` are in-place applicators too, so their annotations reach the
   referring node and the annotation-aware keyword is required there for the same
   reason. A node with neither has all its declarations in one object, so the lexical
   keyword is correct — and keeping it means non-composed schemas are unaffected, byte
   for byte.

4. **A definition closes on its own terms unless every reference to it is composed.** A
   reference is *composed* when the referring node contributes constraints alongside it:
   it declares sibling `properties`, carries a fragment applicator, or sits inside a
   fragment. In each of those cases the referring node (or its composition root) is
   itself closed with `unevaluatedProperties`, which already covers the definition’s
   keys through the propagated annotation — so closing the definition lexically as well
   would reject whatever the siblings declare.
   That is precisely the ubiquitous extension idiom:

   ```yaml
   allOf:
     - $ref: "#/$defs/Base"                    # declares `street`
     - properties: {extra: {type: string}}
   $defs:
     Base: {type: object, properties: {street: {type: string}}}
   ```

   A **standalone** reference — a bare `{"$ref": …}` in non-fragment position, such as a
   property value — has nothing else covering that instance location, so the definition
   must close itself. One standalone reference anywhere is enough to keep it closed; a
   definition used both ways keeps its closure, and the composed use carries the
   residual.

An explicit `additionalProperties` or `unevaluatedProperties` anywhere always wins, so a
schema can opt any object out.
Objects that declare no properties anywhere — free-form mappings — are never closed.

#### Consequences of the annotation model

These follow from “only successful subschemas contribute”, and are worth knowing rather
than discovering.

A property named in an `if` matcher **is** evaluated when the matcher succeeds, so it is
admitted. Given `if: {properties: {secret: {const: "x"}}}` and no `secret` at the root,
`{"secret": "x"}` passes closure while `{"secret": "other"}` is rejected.
The converse bites harder: a failing `if` contributes nothing, so a property named
*only* in a matcher is undeclared whenever the matcher does not fire.
**Declare matched properties at the root as well.**

### What `enforced` does not close

Closure applies at composition roots.
Two shapes are deliberately left open, because closing them lexically would reintroduce
exactly the failure the rules above prevent:

- **Objects declared inline inside a fragment.** Annotations propagate to the
  composition root, and `unevaluatedProperties` there constrains the *root* instance
  object only — it cannot reach a nested instance location.
  An object declared under, say, `then.properties.extra` therefore stays open, and
  closing it lexically would be blind to any sibling fragment constraining the same
  nested location. To restore strictness, declare it as a `$defs` entry and `$ref` it:
  rule 4 keeps a standalone reference’s definition closed.
- **Alternatives nested inside a fragment.** In `allOf: [{anyOf: […]}]` the branches
  inherit fragment status, so rule 1 leaves them open, and rule 2 does not traverse
  alternatives, so the root does not close either.
  The same `anyOf` at the top level does close its branches.
  Closing the root over hoisted branch declarations would give union semantics that
  differ from top-level branch closure, which is a contract decision rather than an
  implementation gap.

Both are pinned as document outcomes in the shared vectors, so a conforming validator
cannot narrow them silently.

The effective status is resolved by the caller (for example a registry contract or a
`--status` flag), falling back to the document’s declared `softschema.status`.

## Source of Truth

A conforming consumer reads structured values in this order:

1. YAML frontmatter payload values.
2. Declared YAML companion data files, when the host project defines that convention.
3. Pure data files.

Markdown body prose and tables are reader-facing and never authoritative.

## Compiled Schemas

A compiled schema is a generated validation contract, usually JSON Schema written as
YAML. It is the language-neutral form of a contract: a Pydantic class or Zod schema
compiles to it (provably identically—the conformance machinery guarantees an equal
`schema_sha256`), and any language can validate against it.

An artifact may bind to its compiled schema with the optional `softschema.schema` key.
The compiled schema a validator uses is resolved in this precedence (highest first):

1. An explicit caller designation: the `--schema` flag, or the schema argument of a
   library call.
2. A host registry binding (a registered contract’s schema path; library path only).
3. The `softschema.schema` document metadata.
4. None—a metadata-only check (contract/status/envelope rules, no schema).

Host-controlled configuration outranks document metadata on purpose: a document must not
silently redirect a host’s validation to a schema the host did not choose.
In a CLI run there is no registry, so the chain is `--schema` > `softschema.schema` >
none, which is what lets a self-describing artifact validate with no flags.

Resolution of a `softschema.schema` value is, by convention, relative to the document
that carries it; this spec requires only that the value be a non-empty string and leaves
the exact resolution to the host, because file layout is situational.
(The reference CLIs accept only relative values in metadata—an absolute path must use
`--schema`—resolve them from the document’s directory, and reject a path whose
normalized result escapes both the document directory and the working directory.)

A compiled schema is not a per-document companion data file.
The two are unrelated: one schema validates many artifacts, while companion data would
pair with a single document.
This spec does not standardize a companion-data discovery mechanism (see Compatibility).

The canonical profile uses JSON Schema Draft 2020-12’s default Format-Annotation
vocabulary. A `format` value, including `date`, `date-time`, `time`, or `duration`, is
descriptive metadata and does not make structural validation fail.
This rule is the same in every runtime and for every document status.
A schema that needs structural lexical enforcement must use an assertion such as a
portable `pattern`; calendar-aware validation belongs in a semantic model.

Regular expressions in `pattern` and in `patternProperties` keys are checked eagerly.
Each is at most 1,024 characters and must compile in both Python and JavaScript.
Named groups, lookbehind, inline flags, numeric backreferences, `\A`, `\Z`, `\z`, `\p`,
and `\P` are outside the portable subset and make the schema invalid.

The `schema_sha256` preimage uses canonical JSON: object keys sort by UTF-16 code unit,
and binary floating-point values use the ECMAScript shortest round-trip spelling.
A Python arbitrary-precision integer outside the portable safe range is rejected rather
than hashed into an identity the TypeScript runtime cannot represent.

The compiled schema and `schema_sha256` identify the structural contract only.
Semantic model constraints that are not emitted as JSON Schema—such as Pydantic coercion
or Zod ISO datetime offset, local-time, and precision options—are outside that identity.
Changing one of those constraints can change a model’s accepted values without causing
structural schema drift.

## Validation Expectations

A conforming validator runs two independent layers and reports their results separately:

- **Structural validation** against the compiled schema (JSON Schema).
- **Semantic validation** against a model (a Pydantic class or a Zod schema) that may
  carry cross-field invariants beyond what JSON Schema expresses.

A validator must reject:

- malformed YAML or frontmatter, including non-mapping frontmatter
- a `softschema` block with unknown keys, an unknown `status`, a malformed `contract`,
  or a non-string/empty `schema` or `envelope`
- a missing envelope when the contract requires one (zero non-`softschema` keys, or the
  designated envelope key is absent)
- envelope ambiguity when auto-detection is in use (multiple top-level non-`softschema`
  keys without an explicit envelope designation)
- a missing or unreadable compiled schema when one is bound (`schema_missing`)
- a bound file that is not a valid schema (`schema_invalid`)
- a JSON Schema validation failure
- a model validation failure
- undeclared payload fields rejected by the `enforced` strictness rule (see Status
  Values)

Validation output is deterministic within each implementation.
Across implementations, structural error records have the same engine-neutral fields and
portable meaning, and machine-readable JSON is compared as parsed data rather than as
presentation bytes. The portable value domain accepts integers only within the IEEE-754
safe-integer range (`abs < 2^53`) so both runtimes retain the same numeric value.

### Matching on structural error records

A structural error record carries both the JSON Schema keyword that failed and a
softschema-owned category:

| `code` | Emitted for | Meaning |
| --- | --- | --- |
| `undeclared_property` | `additionalProperties`, `unevaluatedProperties` | a key the schema does not declare |
| `missing_property` | `required` | a declared key the document omits |
| `invalid_value` | every other mapped keyword | a value the schema rejects |
| `unmapped_keyword` | a keyword with no template yet | a gap in the message table, not a category |

**`kind` + `code` + `path` is the surface to match on.** `validator` and
`validator_value` name the *mechanism* and are diagnostic; `message` wording may improve
within a minor release.

The distinction matters most for closure.
One authoring mistake — an undeclared key — reports `additionalProperties` on a simple
schema and `unevaluatedProperties` on a composed one, so a consumer matching `validator`
sees only half the cases.
Both report `code: undeclared_property`, and both render the same message.

## Generated Sections

A conforming implementation may regenerate Markdown sections from a compiled schema
using HTML comment markers.
This is an optional, advanced feature for keeping a piece of Markdown (such as a
vocabulary table in a runbook) in sync with the schema; it is never part of the basic
artifact shape and does not appear in introductory examples.

```markdown
<!-- softschema:generated kind="enum_table" schema="movie-page.schema.yaml" -->

| Field | Allowed values |
| --- | --- |
| `mpaa_rating` | G, PG, PG-13, R, NC-17, NR |

<!-- /softschema:generated -->
```

Recognized attributes:

| Attribute | Required | Meaning |
| --- | --- | --- |
| `kind` | yes | One of `enum_table`, `field_list`, `vocab`. |
| `schema` | yes | Path to a compiled schema (relative paths resolve from the containing file). |
| `pointer` | yes for `vocab` | JSON Pointer (RFC 6901) to a specific field. |
| `sha256` | no | Informational hash of the schema at render time. |

(The path attribute is `schema`, not `contract`: `contract` is a logical ID, never a
file path.
A marker that uses `contract="...path..."` is rejected with a message pointing
at the rename.)

The output is normative—equal inputs produce byte-equal output, and an implementation is
checked against this spec, not the other way around:

- **`enum_table`**: a GFM table with header row `| Field | Allowed values |`; one row
  per string-enum property of the schema, in the schema’s property order; the field name
  in backticks; allowed values comma-space joined in schema order; a literal `|` in a
  value is escaped as `\|`. A property is enum-valued when it carries an all-string
  `enum`, or the `anyOf: [{enum: …}, {type: "null"}]` nullable shape (whose string-enum
  branch is rendered); any other enum shape is skipped.
  With no enum-valued properties the single row is `| _(no enum fields)_ | _(none)_ |`.
- **`field_list`**: one bullet per top-level property, in schema order:
  `- `name` (type, required): description`—the JSON type label, `required` or
  `optional`, then `: description` only when the property has one.
  Nested properties are not listed (they appear through their parent’s type).
  With no properties the single bullet is `- _(no fields)_`.
- **`vocab`**: one `` - `value` `` bullet per allowed value of the single property
  addressed by `pointer`, in schema order.

A renderer must:

- Replace the body deterministically; the body between the markers is generator-owned
  and authors must not hand-edit it (CI fails on drift).
- Reject an unknown `kind` rather than silently emit a fallback.
- Resolve a missing or unreadable `schema` as an error.

The marker mechanism intentionally follows the same HTML-comment-tag convention as
[markform](https://github.com/jlevy/markform), under a `softschema:` namespace so the
two do not collide (see Compatibility).

## Compatibility and Related Formats

- **frontmatter-format.** The `frontmatter-md` profile matches
  [frontmatter-format](https://github.com/jlevy/frontmatter-format)’s YAML/Markdown
  (`---` delimited) style, and only that style.
  Both softschema implementations implement the same `---` subset and are held to it by
  the shared corpus. Comment-style fences for other file types (HTML, Python, Rust, CSS,
  SQL) that frontmatter-format also defines are out of scope here.
  Frontmatter-format is authoritative for the Markdown fence syntax and requirement that
  parsed frontmatter be a mapping (for example, non-mapping frontmatter is rejected).
  It is not authoritative for the portable YAML value domain: its generic Python readers
  may materialize YAML timestamps as `date` or `datetime` objects, while this spec
  requires implicit date- and timestamp-shaped scalars to remain strings.
- **sidematter-format.** This spec does not adopt
  [sidematter-format](https://github.com/jlevy/sidematter-format)’s per-document
  companion convention (`doc.md` → `doc.meta.yml` / `doc.assets/`). The term “sidecar”
  is reserved for that convention and is not used for compiled schemas.
- **markform.** The generated-section marker mechanism matches markform’s
  HTML-comment-tag convention (`key="value"` attributes) under a `softschema:`
  namespace; there is no formal dependency in either direction.

## Out of Scope

The following are not part of this spec.
A conforming implementation must not treat any of them as valid artifact-format rules:

- A `softschema.values: {location, pointer}` resolver shape, or any envelope-resolution
  mode beyond the one-envelope rule above.
- A generic companion-data discovery mechanism (see sidematter-format above).
- Markdown body parsers, body-form runtimes, or any extraction of structured values from
  body prose or tables.
- A repair loop, alias resolution, or patch protocol.
- A `legacy` status value.
- Provider structured-output adapters.
- Generated-section `view` presets, instance-value mirrors, and URN-based `schema`
  resolution.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
