# softschema

Soft schemas are a practice for adding structure gradually to artifacts that mix human
context and machine-readable values.

They are useful when a human or agent writes a readable document, but code needs a few
values from that document reliably.
The YAML/frontmatter carries the authoritative values.
The Markdown body stays readable.

The pattern is programming-language agnostic.
This repo also ships the first concrete implementation in Python.

## Core Idea

Automation, exactness, and structure are separate axes.
LLMs and agents make it easy to automate work that still has human-like failure modes:
mixed prose, judgment calls, partial structure, and implicit context.

Soft schemas let a project promote only the values downstream tools consume, while
keeping the rest of the artifact readable.

```text
prose
  -> expected sections and vocabulary
  -> YAML/frontmatter values for consumed fields
  -> schema validation at boundaries
  -> pure data or deterministic code when the shape is stable
```

## Artifact Shape

The default shape is Markdown with YAML frontmatter.
Use `softschema.contract` to name the contract for the enclosed payload:

```markdown
---
softschema:
  contract: example.movies:MoviePage/v1
  status: enforced
movie:
  title: Spirited Away
  release_year: 2001
  runtime_minutes: 125
  mpaa_rating: PG
  directors:
    - Hayao Miyazaki
  genres:
    - Animation
    - Adventure
    - Family
  synopsis: >
    Ten-year-old Chihiro and her parents stumble into a mysterious abandoned town
    that turns out to be a spirit world...
  cast:
    - actor: Rumi Hiiragi
      character: Chihiro / Sen
    - actor: Miyu Irino
      character: Haku
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

A 1-2 paragraph prose summary suitable for human readers, followed by optional tables
that mirror the YAML for scanning.
```

The YAML payload is authoritative.
Markdown body prose and tables are reader-facing projections.

The example illustrates the structural variety a softschema artifact can carry:
constrained integers (`release_year`, `runtime_minutes`), an enum (`mpaa_rating`
restricted to `G`, `PG`, `PG-13`, `R`, `NC-17`, `NR`), lists of strings (`directors`,
`genres`), a list of structured records (`cast`), and nested objects (`ratings`). The
full artifact, model, and generated JSON Schema live under
[examples/movie_page/](examples/movie_page/README.md).

## Contract IDs

Recommended style:

```text
namespace:UpperCamelCaseName/version
```

Examples:

- `example.movies:MoviePage/v1`
- `example.docs:IncidentReview/v1`
- `com.acme.docs:IncidentReview/1.0`

The ID names an artifact payload contract, not a required class or import path.

## Try the Python Package

Install dependencies:

```bash
uv sync --all-extras
```

Validate the example:

```bash
uv run softschema validate examples/movie_page/spirited-away.md \
  --model examples.movie_page.model:MoviePage \
  --schema examples/movie_page/movie-page.schema.yaml
```

`validate` reads `softschema.contract`, `softschema.status`, and the single top-level
envelope key from the YAML by default.
Use `--contract`, `--status`, or `--envelope` only to override or disambiguate.

Read the bundled docs from the CLI:

```bash
uv run softschema docs --list
uv run softschema docs --list --json
uv run softschema docs guide
uv run softschema docs example-artifact
uv run softschema skill --brief
```

The examples are plain files under `examples/`. The CLI can print them so an agent or
human can copy from them, but it does not scaffold or mutate another project.

Compile the example schema sidecar:

```bash
uv run softschema compile examples.movie_page.model:MoviePage \
  --contract example.movies:MoviePage/v1 \
  --out examples/movie_page/movie-page.schema.yaml
```

## Repository Layout

```text
docs/                  guide, spec, Python package design, and workflow docs
examples/movie_page/   complete example with model, host integration, artifact, schema
packages/python/       Python implementation and tests
packages/typescript/   future TypeScript/Zod notes only
skills/softschema/     agent-facing usage guidance
```

The root `pyproject.toml` builds the Python package from
`packages/python/src/softschema`. This keeps the first release simple while leaving room
for a future TypeScript package.

## Docs

- [Softschema Guide](docs/softschema-guide.md)
- [Softschema Spec](docs/softschema-spec.md)
- [Python Package Design](docs/softschema-python-design.md)
- [Installing uv and Python](docs/installation.md)
- [Development](docs/development.md)
- [Publishing](docs/publishing.md)
- [Movie Page Example](examples/movie_page/README.md)

<!-- This document follows std-doc-guidelines.md.
Review guidelines before editing.
-->
