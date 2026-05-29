# Softschema Spec

Softschema is a file convention for Markdown/YAML artifacts that are readable by humans
and structured enough for tools.
The spec is programming-language agnostic.
The Python package in this repository is one implementation.

For the adoption guide, examples, and tutorials, see
[Softschema Guide](softschema-guide.md).
This document defines what an artifact must look like and how a validator must treat it.

## Scope

This spec defines the artifact format, the recognized metadata, and the validation
expectations a conforming implementation must honor.
It does not define how to author artifacts, how to migrate existing documents, or how a
specific implementation should package itself.

## Artifact Profiles

A conforming artifact uses one of two profiles:

| Profile | Description |
| --- | --- |
| `frontmatter-md` | Markdown file with YAML frontmatter. The frontmatter carries the structured payload; the Markdown body is reader-facing prose. |
| `pure-yaml` | YAML file with no Markdown body. The whole document is the structured payload. |

The frontmatter-md profile is the primary shape.
A pure-yaml artifact follows the same metadata and envelope rules; references to
“frontmatter” below apply to the document root in the pure-yaml case.

## Frontmatter Artifact Shape

```markdown
---
softschema:
  contract: example.movies:MoviePage/v1
  status: enforced
movie:
  title: Spirited Away
  release_year: 2001
  mpaa_rating: PG
  directors:
    - Hayao Miyazaki
  genres:
    - Animation
    - Adventure
    - Family
  synopsis: >
    Ten-year-old Chihiro stumbles into a spirit world and must work in a magical
    bathhouse to free her parents and return home.
  ratings:
    rotten_tomatoes:
      critics_percent: 96
      audience_percent: 96
      critic_review_count: 225
    imdb:
      score: 8.6
      total_votes: 850000
---
# Spirited Away (2001)

Reader-facing prose body.
```

The YAML frontmatter is the only authoritative source of structured values.
The Markdown body may mirror values in prose or tables for human readers, but a
conforming consumer must not parse body text as a source of structured values.

## Metadata

The `softschema` mapping is the recognized metadata block in the frontmatter:

```yaml
softschema:
  contract: example.movies:MoviePage/v1
  status: enforced
```

| Field | Required | Meaning |
| --- | --- | --- |
| `contract` | yes for self-describing documents | Stable payload contract ID |
| `status` | no | Boundary maturity: `soft`, `permissive`, or `enforced` |

A `softschema` block with unknown keys, unknown status values, or a malformed `contract`
value is a validation error.

## Envelope Selection

A normal artifact carries one top-level payload key beside `softschema`. That key is the
envelope, and its value is the root validated against the contract.

An implementation must:

- Accept exactly one non-`softschema` top-level key and treat it as the envelope.
- Allow callers to specify the envelope explicitly when more than one non-`softschema`
  top-level key exists.
- Reject documents with zero or multiple non-`softschema` top-level keys when no
  explicit envelope is supplied.

## Contract IDs

A contract ID names an artifact payload contract.

The recommended form is `namespace:UpperCamelCaseName/version`. Examples:

- `example.movies:MoviePage/v1`
- `example.docs:IncidentReview/v1`
- `com.acme.docs:IncidentReview/1.0`

A contract ID may map to a Pydantic model, Zod schema, JSON Schema sidecar, database
record, or hand-authored validator.
It is not required to be an import path or a class name.

## Status Values

| Status | Meaning |
| --- | --- |
| `soft` | A convention exists, but no boundary schema is enforced |
| `permissive` | Known fields validate; extension fields may be allowed by the source model |
| `enforced` | The schema is authoritative at the boundary |

`status` records intended maturity.
It does not change validation behavior by itself; whether a model allows extra fields is
configured on the source model.

## Source of Truth

A conforming consumer reads structured values in this order:

1. YAML frontmatter payload values.
2. Declared YAML data sidecars, when the host project defines that convention.
3. Pure data files.

Markdown body prose and tables are reader-facing and never authoritative.

## Schema Sidecars

A schema sidecar is a generated validation contract, usually JSON Schema written as
YAML. Schema sidecars are implementation artifacts and are not normally referenced from
authored document metadata.

A schema sidecar is not a data sidecar.
A data sidecar stores payload values outside the frontmatter.
This spec allows projects to declare data sidecars by convention but does not
standardize a data-sidecar discovery mechanism in v0.1.

## Validation Expectations

A conforming validator runs two independent layers and reports their results separately:

- **Structural validation** against a JSON Schema sidecar.
- **Semantic validation** against an implementation schema (such as a Pydantic model or
  a Zod schema) that may carry cross-field invariants beyond what JSON Schema expresses.

A validator must reject:

- malformed YAML or frontmatter
- a `softschema` block with unknown keys, an unknown `status`, or a malformed `contract`
- a missing envelope when the contract requires one
- envelope ambiguity (multiple top-level non-`softschema` keys without an explicit
  envelope choice)
- a missing or unreadable schema sidecar when the binding declares one
- a JSON Schema validation failure
- an implementation-schema validation failure

## Generated Sections

A conforming implementation may regenerate Markdown sections from a schema using HTML
comment markers. The marker pair is namespaced so it does not collide with other
code-generators:

```markdown
<!-- softschema:generated kind="enum_table" contract="path/to/schema.yaml" -->
| Field | Allowed values |
| --- | --- |
| `mpaa_rating` | G, PG, PG-13, R, NC-17, NR |
<!-- /softschema:generated -->
```

Recognized attributes:

| Attribute | Required | Meaning |
| --- | --- | --- |
| `kind` | yes | One of `enum_table`, `field_list`, `vocab`. |
| `contract` | yes | Path to a compiled JSON Schema sidecar (relative paths resolve from the containing file). |
| `pointer` | yes for `vocab` | JSON Pointer (RFC 6901) to a specific field. |
| `sha256` | no | Informational hash of the schema bundle at render time. |

The body between the markers is fully owned by the generator.
Authors must not hand-edit it; CI fails on drift.
A renderer must:

- Replace the body deterministically; equal inputs produce byte-equal output.
- Reject unknown `kind` values rather than silently emit a fallback.
- Resolve a missing or unreadable `contract` as an error.

## Out of Scope for v0.1

The following are explicitly not part of v0.1. A conforming implementation must not
treat any of them as valid artifact-format rules:

- A `softschema.values: {location, pointer}` resolver shape, or any envelope-resolution
  mode beyond the one-envelope rule above.
- A generic data-sidecar discovery mechanism.
- Markdown body parsers, body-form runtimes, or any extraction of structured values from
  body prose or tables.
- A repair loop, alias resolution, patch protocol, or materialized canonical sidecar.
- A `legacy` status value.
- Provider structured-output adapters (planned, but not part of v0.1).
- Generated-section `view` presets, instance-value mirrors, and URN-based `contract`
  resolution (deferred extensions of the generated-section feature above).

<!-- This document follows std-doc-guidelines.md.
Review guidelines before editing.
-->
