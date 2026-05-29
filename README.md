# softschema

Soft schemas are a practice for adding structure gradually to artifacts that mix human
context and machine-readable values.

They are useful when a document is valuable as context for humans and agents and also
needs a few values that downstream code or agents can read reliably.
Keeping prose and structured values in one artifact is more context-efficient and more
flexible than splitting them: a reader (human or agent) has only one place to look, and
each value can stay as loose prose until a downstream consumer needs it formal.

The practice is language-neutral.
This repo ships a spec and an implementation in Python.

It’s generally easiest to do this with Markdown and YAML frontmatter.
The YAML carries the structured values.
The Markdown body stays readable for humans and agents and offers additional context.

**Soft schemas** name the general practice; **softschema** names both this repository’s
Markdown-and-YAML spec and the matching `softschema` CLI that implements it.
The CLI is a Python package usable as a command-line tool or library for formatting,
compilation, validation, and other common workflows.

## Core Idea

A *hard* schema imposes structure up front: define a rigid contract, then reject
anything that doesn’t fit.
That suits data that is already uniform, but it is a poor fit for documents a human or
agent writes, where most of the content is prose and only a few values need to be
machine-readable.

A soft schema adds structure gradually instead.
Structure runs along a spectrum, and each value moves along it only when it earns the
move:

```text
prose
  -> expected sections and vocabulary
  -> YAML/frontmatter values for consumed fields
  -> schema validation at boundaries
  -> pure data or deterministic code when the shape is stable
```

Promote a value into YAML when a tool reads it, validate it at the boundary when
correctness matters, and tighten enforcement over time.
Each promotion buys efficiency for some downstream consumer, so structure and efficiency
grow together, value by value.
Everything else stays readable Markdown.
The structured values live in the YAML payload, the boundary a tool reads, while the
prose body stays unconstrained.
Structure has real costs in authoring effort and rigidity, and adding it before a
consumer needs it costs more than leaving it loose: a contract with consumers is harder
to loosen than prose is to tighten.
So add structure where it pays for itself.
This fits the file artifacts that pass between steps of an agent process, where each
artifact mixes the context a step produces with the few values the next step consumes.
It works especially well in pipelines built for coding agents, which can call the
`softschema` CLI to test and validate the code, docs, and data they produce, alongside
the linters, tests, and type checkers they already run.

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

Hayao Miyazaki’s animated fantasy follows ten-year-old Chihiro into a spirit world, where
she works in a bathhouse for the gods to free her parents from a witch’s curse. It won the
2003 Academy Award for Best Animated Feature.

Critics and audiences both score it 96% on Rotten Tomatoes; IMDb users rate it 8.6/10.
```

The YAML payload is authoritative.
The Markdown body overlaps with it but need not match it field for field: here the prose
adds the film’s Oscar win and leaves out the cast and genres, while a consumer reads
only the YAML.

Only the `softschema` block and the chosen envelope key (`movie:` above) are
softschema’s concern.
Additional top-level frontmatter keys (such as `title:`, `description:`, `tags:`, or any
other host-specific metadata) are fine and ignored by softschema, so an artifact can
coexist with whatever frontmatter conventions a static-site generator, doc indexer, or
other tool already expects.

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

`validate` reads `softschema.contract`, `softschema.status`, and (when there is exactly
one non-`softschema` top-level key) infers it as the envelope.
Pass `--envelope` to designate the payload when other frontmatter keys (such as
`title:`, `tags:`, or other host metadata) sit alongside; `--contract` and `--status`
override the corresponding `softschema:` fields.

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
uvx softschema@0.1.1 --help            # entry point with bootstrap pointers
uvx softschema@0.1.1 skill --brief     # ~12-line operating brief
uvx softschema@0.1.1 docs guide        # full mental model and adoption path
```

Self-install the skill into a project so any agent working in the repo finds it
natively:

```bash
uvx softschema@0.1.1 skill --install
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

## Docs

- [Softschema Guide](docs/softschema-guide.md)
- [Softschema Spec](docs/softschema-spec.md)
- [Python Package Design](docs/softschema-python-design.md)
- [Installing uv and Python](docs/installation.md)
- [Development](docs/development.md)
- [Publishing](docs/publishing.md)
- [Movie Page Example](examples/movie_page/README.md)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
