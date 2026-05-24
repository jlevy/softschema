# Softschema Spec

Softschema is a file convention for Markdown/YAML artifacts that are readable by humans
and structured enough for tools.

The spec is programming-language agnostic. The Python package in this repository is one
implementation.

## Scope

This spec defines:

- document metadata
- payload envelopes
- contract IDs
- status values
- source-of-truth rules
- validation expectations

It does not define a Markdown body parser, a form runtime, a repair loop, a provider
structured-output adapter, a process graph report, or a TypeScript implementation.

## Artifact Shape

The primary shape is Markdown with YAML frontmatter:

```markdown
---
softschema:
  contract: example.movies:MoviePage/v1
  status: enforced
movie:
  title: Spirited Away
  release_year: 2001
  ratings:
    rotten_tomatoes:
      critics:
        label: Tomatometer
        score_percent: 96
        total_reviews: 225
      audience:
        label: Popcornmeter
        score_percent: 96
        total_ratings: 250000
        total_ratings_display: 250,000+
---
# Spirited Away (2001)

Rotten Tomatoes shows a 96% Tomatometer based on 225 critic reviews and a 96%
Popcornmeter based on 250,000+ audience ratings.
```

The YAML frontmatter is authoritative for structured consumers. The Markdown body may
repeat the same values in prose or tables, but tools must not parse body text as the
source of structured values.

## Metadata

`softschema` is an optional mapping in the YAML frontmatter.

```yaml
softschema:
  contract: example.movies:MoviePage/v1
  status: enforced
```

Fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `contract` | yes for self-describing documents | Stable payload contract ID |
| `status` | no | Boundary maturity: `soft`, `permissive`, or `enforced` |

Invalid `softschema` metadata is a validation error.

## Envelope

Normal Markdown artifacts use one top-level payload key beside `softschema`.

```yaml
softschema:
  contract: example.movies:MoviePage/v1
movie:
  title: Spirited Away
```

The envelope key is the root of the values validated by the contract. A CLI or host can
infer the envelope when exactly one non-`softschema` top-level key exists. If multiple
payload keys exist, the caller should specify the envelope.

## Contract IDs

Contract IDs name artifact payload contracts.

Recommended form:

```text
namespace:UpperCamelCaseName/version
```

Examples:

- `example.movies:MoviePage/v1`
- `example.docs:IncidentReview/v1`
- `com.acme.docs:IncidentReview/1.0`

A contract ID can map to a Pydantic model, Zod schema, JSON Schema sidecar, database
record, or custom validator. It is not required to be an import path or class name.

## Status Values

| Status | Meaning |
| --- | --- |
| `soft` | A convention exists, but no boundary schema is enforced |
| `permissive` | Known fields validate, while extension fields may be allowed by the source model |
| `enforced` | The schema is authoritative at the boundary |

Status records intended maturity. It does not change validation behavior by itself.
Validation behavior comes from the selected implementation schema.

## Validation

Validation has two common layers:

- Structural validation with JSON Schema
- Semantic validation with an implementation schema such as Pydantic

The CLI reads `softschema.contract`, `softschema.status`, and a single top-level
envelope key from the artifact by default:

```bash
softschema validate examples/movie_page/spirited-away.md \
  --model examples.movie_page.model:MoviePage \
  --schema examples/movie_page/movie-page.schema.yaml
```

Callers may pass `--contract`, `--status`, or `--envelope` to override document metadata
or disambiguate a document with multiple payload keys.

## Schema Sidecars

A schema sidecar is a generated validation contract, usually JSON Schema written as
YAML.

Schema sidecars are implementation artifacts. They are not normally referenced from
authored document metadata.

Schema sidecars are not data sidecars. A data sidecar stores payload values outside the
frontmatter. This spec allows projects to declare data sidecars by convention, but it
does not standardize a data-sidecar discovery mechanism in the first version. The
default artifact shape keeps consumed values in frontmatter.

## Source of Truth

Structured consumers should read, in order of project convention:

1. YAML frontmatter payload values
2. Declared YAML data sidecars, when the host project defines that convention
3. Pure data files

Markdown body prose and tables are reader-facing. They can mirror structured values, but
they are not authoritative.

## Embedded Docs and Examples

Implementations may bundle the guide, spec, skill instructions, and examples for agent
discovery. Bundling docs does not make example files a scaffolding API. Examples are
copyable references unless a specific implementation explicitly provides project
mutation commands.

<!-- This document follows std-doc-guidelines.md. Review guidelines before editing. -->
