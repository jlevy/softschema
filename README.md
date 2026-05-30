# softschema

## What Are Soft Schemas?

Soft schemas are a practice for adding structure gradually to artifacts that mix
flexible document context and machine-readable values.

The idea is quite simple, but I’ve found it non-obvious enough that coding agents do not
come up with this approach themselves.

However if given the information and tools in this repo, soft schemas are unreasonably
effective. Agents become far better at designing and building complex workflows that mix
structured and unstructured data, such as document processing, data extraction,
scientific or financial analyses, and many similar applications.

**Soft schemas** are what we call the general practice.
**Softschema** is the name of this repository’s Markdown-and-YAML spec and the matching
`softschema` CLI that implements it.

## How Do Soft Schemas Work?

The practice is very simple and language neutral.
The simplest approach is to use artifacts in a process or pipeline that are Markdown
documents with YAML frontmatter.
The YAML carries selected structured values.
The Markdown body stays readable for humans and agents and offers additional context.
There are no strict rules about duplicating content between Markdown and YAML, but you
can gradually adjust and enforce rules.

A *hard* schema imposes structure up front: define a rigid contract, then reject
anything that doesn’t fit.
That suits data that is already uniform, but it is a poor fit for documents a human or
agent writes, where most of the content is prose and only a few values need to be
machine-readable.

A *soft* schema lets you add structure gradually to the artifacts that pass between
steps of a workflow.

Structure runs along a spectrum, and each value moves along it only when it earns the
move:

```text
plain Markdown prose
  -> plain Markdown with a few YAML frontmatter values for specific fields
  -> plain Markdown with more YAML fields and a bit of loose validation
  -> plain Markdown with YAML frontmatter fully validated against JSON Schema (or Pydantic/Zod)
  -> plain Markdown with separate structured data files or database records
```

The structured values live in the YAML payload, the boundary a tool reads, while the
prose body stays unconstrained.
Validation rules can be easily removed or changed if greater flexibility is needed.

Promote a value into YAML when a tool reads it, validate it at the boundary when
correctness matters, and tighten enforcement over time.
Each promotion buys efficiency for some downstream consumer, so structure and efficiency
grow together, value by value.

Start with processes and data defined in Markdown with data right in the text.
Have coding agents try them.
Only add structure when it pays for itself.

## When and Why Are Soft Schemas Useful?

You should consider using soft schemas if:

1. You wish to have coding agents perform complex processing workflows involving both
   data and documents

2. Some aspects of the workflow involve structured data that is processed efficiently
   via code and some aspects are ill-defined

3. The boundary between structured and unstructured data might evolve as you scale and
   improve the workflows

A plain text document offers flexible context for humans and agents.
Structured records are far better when code or agents need to read values consistently
and efficiently.

Balancing these needs is often difficult and the source of significant complexity.

Some engineers see the goal of productionizing an agent workflow as the process of
converting it to reusable code or structured forms, like relational database schemas.

But the reality is that *prematurely structuring data* before you understand the
structures that best serve a workflow involving code and agents has a cost.
At the same time, *poorly defined structure* has costs in consistency and efficiency.

What is actually needed is **gradual addition of structure** and **flexible addition of
textual context** at any time.

Soft schemas are simple habits and conventions to make the boundary between structured
and unstructured data easier to adjust in either direction as a workflow’s needs for
flexibility, consistency, and efficiency evolve (code vs LLM calls).
Keeping prose and structured values in one artifact is more convenient and
context-efficient. A reader (human or agent) has only one place to look, and information
can stay as loose prose until a downstream consumer needs it in more formal schemas.

## What Is This Repo?

This repo is simply:

- A few documents for use by agents, including a [spec](docs/softschema-spec.md)
  defining soft schema file format conventions for Markdown documents with YAML
  frontmatter.

- A simple [Python CLI](docs/softschema-python-design.md) that handles formatting,
  compilation, validation, and other common workflows on soft schema-style documents.

The CLI can be used directly, as a library, or installed as a skill.

For the full conceptual reference and adoption playbooks, see the
[Softschema Guide](docs/softschema-guide.md).

## Example Artifact Shape

The default shape is Markdown with YAML frontmatter.
Use `softschema.contract` to name the contract for the enclosed payload:

```markdown
---
title: Spirited Away (2001)
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
    that turns out to be a spirit world. After her parents are transformed into pigs,
    Chihiro must take a job in a magical bathhouse run by the witch Yubaba and find a
    way to break the spell so the family can return home.
  cast:
    - actor: Rumi Hiiragi
      character: Chihiro / Sen
    - actor: Miyu Irino
      character: Haku
    - actor: Mari Natsuki
      character: Yubaba
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

*Spirited Away* is Hayao Miyazaki’s animated fantasy about ten-year-old Chihiro, who
slips into a spirit world and takes a job in a bathhouse for the gods to free her
parents from the witch Yubaba.
It won the 2003 Academy Award for Best Animated Feature.

Rotten Tomatoes shows a 96% Tomatometer from 225 critic reviews and a 96% Popcornmeter
from the audience; IMDb users give it 8.6 out of 10 across more than 850,000 votes.

## Movie Details

| Field | Value |
| --- | --- |
| Title | Spirited Away |
| Release year | 2001 |
| Runtime | 125 minutes |
| MPAA rating | PG |
| Director | Hayao Miyazaki |
| Genres | Animation, Adventure, Family |

## Lead Cast

| Actor | Character |
| --- | --- |
| Rumi Hiiragi | Chihiro / Sen |
| Miyu Irino | Haku |
| Mari Natsuki | Yubaba |

## Ratings

| Source | Score | Count |
| --- | ---: | ---: |
| Rotten Tomatoes Critics | 96% Tomatometer | 225 reviews |
| Rotten Tomatoes Audience | 96% Popcornmeter | — |
| IMDb | 8.6 / 10 | 850,000+ votes |
```

The YAML payload is authoritative; a consumer reads it.
The Markdown body overlaps with it but is for human readers: the body’s tables mirror
some YAML fields for the reader’s convenience, the prose adds context like the film’s
Academy Award (which no structured field carries), and the YAML alone carries downstream
fields such as `critic_review_count`.

Only the `softschema` block and the chosen envelope key (`movie:` above) are
softschema’s concern.
Additional top-level frontmatter keys, such as the `title:` above (or fields like
`description:`, `tags:`, or any other host-specific metadata), are a separate concern.
softschema neither forbids nor interprets them, so an artifact can coexist with whatever
frontmatter conventions a static-site generator, doc indexer, or other tool already
expects. When an artifact carries any such extra top-level key, the validator can no
longer infer the envelope on its own; pass `--envelope` (or set `envelope_key` on the
registered contract) to designate the payload.

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

Install dependencies (see [Installation](docs/installation.md) for uv and Python setup):

```bash
uv sync --all-extras
```

Validate the example:

```bash
uv run softschema validate examples/movie_page/spirited-away.md \
  --model examples.movie_page.model:MoviePage \
  --schema examples/movie_page/movie-page.schema.yaml \
  --envelope movie
```

`validate` reads `softschema.contract` and `softschema.status` from the document.
`--envelope movie` designates the payload key, which the example needs because the
artifact also carries a top-level `title:` that softschema does not interpret.
When an artifact has exactly one non-`softschema` top-level key, that key is inferred as
the envelope automatically and `--envelope` is unnecessary.
`--contract` and `--status` override the corresponding `softschema:` fields.

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

## Use as an Agent Skill

The `softschema` CLI ships as a [`SKILL.md`](https://agentskills.io) following the open
Agent Skills standard discovered by Claude Code, Codex, Gemini CLI, Cursor, Copilot, and
~20 other coding agents.
Pointing an agent at the CLI is enough to bootstrap its understanding of the soft-schema
approach: the `--help` epilog routes it to a brief and the bundled docs.

```bash
uvx softschema@0.1.3 --help            # entry point with bootstrap pointers
uvx softschema@0.1.3 skill --brief     # ~12-line operating brief
uvx softschema@0.1.3 docs guide        # full mental model and adoption path
```

Self-install the skill into a project so any agent working in the repo finds it
natively:

```bash
uvx softschema@0.1.3 skill --install
# writes:
#   .agents/skills/softschema/SKILL.md   (Codex, Gemini CLI, cross-agent installers)
#   .claude/skills/softschema/SKILL.md   (Claude Code mirror)
```

Both mirrors carry a `DO NOT EDIT` marker and the version that wrote them.
Re-run `softschema skill --install` to refresh after upgrading the CLI.

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

## Development and Contributing

See [Development](docs/development.md) for repo setup, common commands, CI checks,
release workflow, and pointers to the installation and publishing docs.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
