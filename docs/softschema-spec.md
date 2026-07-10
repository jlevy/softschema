# softschema Spec

softschema is a file convention for Markdown/YAML artifacts that are readable by humans
and structured enough for tools.
The spec is programming-language agnostic.
This repository ships two interchangeable implementations of the spec, a Python/Pydantic
package and a TypeScript/Zod package, held to exact behavioral parity.

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
run_id: 2026-04-12T18-03-00Z
summary: regression vs baseline
```

## Portable YAML Value Domain

Artifacts, compiled schemas, and supplied schema resources use the same bounded,
JSON-compatible YAML subset.
A value may contain objects with string keys, arrays, strings, booleans, null, finite
IEEE-754 binary64 numbers, and mathematically integral numbers from `-9007199254740991`
through `9007199254740991`.

Validation rejects duplicate or non-string keys, custom tags, aliases, merge keys,
cycles, non-finite numbers, unsafe integers, binary and set values, explicit timestamp
values, and other YAML-specific runtime types.
Plain date-looking and timestamp-looking scalars remain strings.
Numeric scalars are interpreted from their exact spelling before binary64 conversion.
Every numeric spelling of negative zero normalizes to `0`.

The default limits are:

- 8 MiB of encoded input per artifact or schema resource
- 64 MiB across a root schema and its supplied resource bundle
- 256 total schema resources, including the root
- 100,000 representation nodes per resource
- a maximum representation depth of 128
- 1 MiB of Unicode code points per scalar

Byte limits apply before parsing.
Node, depth, scalar, alias, and merge checks apply before ordinary object construction.
Already-materialized library resources are sized as compact, key-sorted UTF-8 JSON after
normalization. Trusted library callers may set explicit lower or higher limits through
`ValidationLimits` in Python or `validationLimits` in TypeScript; command-line
validation always uses the defaults.

A non-portable artifact produces `parse_error` with reason `value_domain`. A
non-portable compiled schema or supplied schema resource produces `schema_invalid` with
reason `value_domain`. Both records carry an RFC 6901 path and omit parser-specific
prose.

## Artifact Parse and Access Failures

Validation distinguishes readable artifact failures from filesystem access failures.
It never exposes YAML-parser or operating-system prose in the result:

| Kind and reason | Stable message | Exit |
| --- | --- | --- |
| `parse_error/frontmatter` | `artifact frontmatter delimiters are malformed` | 1 |
| `parse_error/syntax` | `artifact is not valid YAML` | 1 |
| `parse_error/root` | `artifact YAML root must be a mapping` | 1 |
| `parse_error/value_domain` | `artifact contains a non-portable YAML value` | 1 |
| `input_error/not_found` | `artifact path does not exist` | 2 |
| `input_error/unreadable` | `artifact path cannot be read` | 2 |
| `input_error/directory_requires_recursive` | `artifact directory requires --recursive` | 2 |

Every record carries `source`. A value-domain record also carries an RFC 6901 `path`.
The typed parsing boundary retains line and column information when the YAML parser
provides it, but the legacy single-file JSON serializer omits locations.
Diagnostic-v1 outputs may include them.

The CLI selects storage shape explicitly with `--profile frontmatter-md|pure-yaml` and
defaults to `frontmatter-md`. It does not infer a profile from a filename extension.

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
  treats every object schema that declares `properties` but omits `additionalProperties`
  as `additionalProperties: false`. An explicit `additionalProperties` value in the
  schema (true, false, or a subschema) always wins, so a schema can opt specific objects
  out of strictness. Object schemas without `properties` (free-form mappings) are
  unaffected. The overlay applies at validation time only; it never changes the compiled
  schema.

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

### Portable Regular Expressions

The `pattern` and `patternProperties` keywords use `portable-regex-v1`. This profile has
ECMA-262 Unicode semantics, uses unanchored search when the pattern is not anchored, and
applies no flags. It keeps the useful common syntax below while excluding constructs
whose meaning or availability differs across Python and JavaScript engines.

```text
pattern      = alternative *( "|" alternative )
alternative  = *piece
piece        = atom [ quantifier ]
atom         = literal / "." / "^" / "$" / escape / class / group
group        = "(" pattern ")" / "(?:" pattern ")"
class        = "[" [ "^" ] 1*class-item "]"
class-item   = class-atom / class-atom "-" class-atom
quantifier   = ( "*" / "+" / "?" / bounded ) [ "?" ]
bounded      = "{" bound "}" / "{" bound "," [ bound ] "}"
bound        = "0" / ( %x31-39 *%x30-39 ) ; 0 through 1000
```

In that grammar:

- A `literal` is one Unicode scalar other than a regular-expression syntax character.
  Escape a syntax character to match it literally.
- A class is non-empty.
  An unescaped `-` is literal only in the first or last class position; escape it
  elsewhere. Escape `^`, `[`, or `]` when it is a class literal.
  A range must have scalar endpoints in ascending code-point order.
- Supported escapes are escaped syntax characters; `\n`, `\r`, `\t`, `\f`, and `\v`;
  two-digit `\xHH`; four-digit, non-surrogate `\uHHHH`; `\d`, `\D`, `\w`, `\W`, `\s`,
  and `\S`. A class may use the digit and word shorthands, but not the whitespace
  shorthands; write `(?:\s|\S)` when a class-independent any-character expression is
  needed.
- `\d` and `\w` are ASCII sets, as in ECMA-262. `\s` is the ECMA-262 whitespace and
  line-terminator set.
  Dot excludes LF, CR, U+2028, and U+2029. `$` means only the true end of the string; it
  does not match before a final newline.
- An assertion (`^` or `$`) cannot be quantified.
  A bounded quantifier has no leading zero, its upper bound is not less than its lower
  bound, and neither bound exceeds 1000.

The profile rejects lookaround, backreferences, word-boundary assertions, named and
atomic groups, inline flags, Unicode property escapes, possessive quantifiers, surrogate
escapes, and ambiguous future character-class operators.
A schema loader validates every actual `pattern` and `patternProperties` schema location
before invoking its JSON Schema engine; pattern-shaped data under annotation keywords
such as `examples` is not schema and is not inspected.
An invalid or unsupported expression produces `schema_invalid` with reason `pattern`,
the JSON Pointer in `schema_path`, and the original expression in `pattern`.

Python validators lower the few divergent tokens in a private in-memory schema copy;
TypeScript validators execute the authored ECMA-262 expression directly.
Lowering never changes the authored file, canonical compiled schema, or `schema_sha256`,
and structural errors report the original expression.
The shared machine-readable syntax and matching vectors are
`tests/parity/portable-patterns.json` in the source repository.

This is an interoperability profile, not a proof that a backtracking expression is
linear-time. Schema authors should still avoid nested ambiguous repetition, and hosts
should apply the validation limits defined for untrusted artifacts.

### Format Annotations

The default Draft 2020-12 profile uses `annotation-only-v1` format semantics.
Every string value of `format`—both a standard name such as `date` or `email` and an
unknown extension name—is metadata for downstream consumers and never changes whether an
instance is structurally valid.
Known and unknown formats must produce no validator warning, logger output, or stderr.
Other assertions beside `format` continue to apply normally.

Semantic validation remains independent: a Pydantic or Zod model may enforce an email,
URI, date, or domain-specific representation even when structural validation treats the
JSON Schema `format` as an annotation.
Use such a trusted semantic model, or an ordinary portable JSON Schema assertion such as
`pattern`, when a boundary must reject malformed formatted values.

The reference Python validator does not supply a format checker for instance validation.
The TypeScript validator configures Ajv with `validateFormats: false`. Both choices are
explicit so installing a format plug-in or upgrading an engine cannot silently turn
annotations into assertions.
The shared machine-readable vectors are `tests/parity/format-annotations.json` in the
source repository.

A future format-assertion mode, if added, must use a separately versioned, explicit
opt-in vocabulary and cross-runtime conformance vectors.
No such assertion vocabulary is part of `annotation-only-v1`.

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

Validation output is deterministic across conforming implementations: structural error
records share an engine-neutral shape and message wording, and numbers — in an error
record’s `value`/`validator_value`, in a synthesized message, and in an echoed payload —
render in a canonical form, where a whole-valued number carries no trailing fraction
(`2`, not `2.0`). Output is byte-identical for every number an implementation can
represent exactly: integers and whole-valued numbers within the IEEE-754 safe-integer
range (`abs < 2^53`), and ordinary floats.
A whole-valued magnitude at or beyond 2^53 is out of scope, because an
arbitrary-precision integer runtime and a double-only runtime cannot always render it
identically; validated payloads should avoid such literals.

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
file path. This is a 0.2.0 change; a marker that still uses `contract="...path..."` is
rejected with a message pointing at the rename.)

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
  The Python implementation consumes the `frontmatter-format` library; the TypeScript
  implementation implements the same `---` subset and is held to it by the golden
  corpus. Comment-style fences for other file types (HTML, Python, Rust, CSS, SQL) that
  frontmatter-format also defines are out of scope here.
  Where the implementations would differ from frontmatter-format’s Markdown rules,
  frontmatter-format is authoritative (for example, non-mapping frontmatter is
  rejected).
- **sidematter-format.** A future version may adopt
  [sidematter-format](https://github.com/jlevy/sidematter-format)’s per-document
  companion convention (`doc.md` → `doc.meta.yml` / `doc.assets/`) for companion data.
  The term “sidecar” is reserved for that future alignment and is not used for compiled
  schemas. Not specified now.
- **markform.** The generated-section marker mechanism matches markform’s
  HTML-comment-tag convention (`key="value"` attributes) under a `softschema:`
  namespace; there is no formal dependency in either direction.

## Out of Scope for v0.2

The following are explicitly not part of v0.2. A conforming implementation must not
treat any of them as valid artifact-format rules:

- A `softschema.values: {location, pointer}` resolver shape, or any envelope-resolution
  mode beyond the one-envelope rule above.
- A generic companion-data discovery mechanism (see sidematter-format above).
- Markdown body parsers, body-form runtimes, or any extraction of structured values from
  body prose or tables.
- A repair loop, alias resolution, or patch protocol.
- A `legacy` status value.
- Provider structured-output adapters (planned, but not part of v0.2).
- Generated-section `view` presets, instance-value mirrors, and URN-based `schema`
  resolution (deferred extensions of the generated-section feature above).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
