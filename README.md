# softschema

Soft schemas: gradual, practical validation for Markdown/YAML artifacts that mix prose
and structured data—built for humans and coding agents.

## Quick Start

Try it anywhere, with nothing installed but [uv](https://docs.astral.sh/uv/) or Node.
Print the bundled example artifact and its compiled schema, then validate—the artifact
is fully self-describing, so no flags are needed:

```bash
uvx softschema@latest docs example-artifact > spirited-away.md
uvx softschema@latest docs example-schema > movie-page.schema.yaml
uvx softschema@latest validate spirited-away.md
```

(Or `npx softschema@latest ...` for the Node implementation; the two are
interchangeable.)

To set up softschema in a repository with an agent, tell the agent:

> Run `uvx softschema@latest --help` (for the Python implementation) or
> `npx softschema@latest --help` (for the Node implementation) and follow the
> instructions to set up softschema for this repo as a skill.

The help output points the agent to `skill --install`, which writes discoverable
`SKILL.md` mirrors for Codex, Claude Code, Gemini CLI, and other coding agents.

## What Are Soft Schemas?

Soft schemas are a practice for adding structure gradually to artifacts that mix
flexible document context and machine-readable values.

The idea is quite simple, but I’ve found it non-obvious enough that coding agents do not
come up with this approach themselves.

However, if given the information and tools in this repo, soft schemas are unreasonably
effective. Agents become far better at designing and building complex workflows that mix
structured and unstructured data, such as document processing, data extraction,
scientific or financial analyses, and many similar applications.

**Soft schemas** are what we call the general practice.
**softschema** is the name of this repository’s Markdown-and-YAML spec and the matching
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

## The Artifact Shape

The default shape is Markdown with YAML frontmatter.
The `softschema:` block is the self-description quartet: `contract` names the payload
contract, `schema` points at the compiled JSON Schema (relative to the document),
`envelope` names the payload key, and `status` sets validation strictness:

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

*Spirited Away* is Hayao Miyazaki's animated fantasy about ten-year-old Chihiro, who
slips into a spirit world and takes a job in a bathhouse for the gods to free her
parents from the witch Yubaba.
It won the 2003 Academy Award for Best Animated Feature.
```

The YAML payload is authoritative; a consumer reads it.
The Markdown body overlaps with it but is for human readers: the prose adds context like
the film’s Academy Award (which no structured field carries), and the full example’s
body mirrors some YAML fields as tables for the reader’s convenience.

Only the `softschema` block and the declared envelope key (`movie:` above) are
softschema’s concern.
Additional top-level frontmatter keys, such as the `title:` above (or `description:`,
`tags:`, or any other host-specific metadata), are a separate concern: softschema
neither forbids nor interprets them, so an artifact can coexist with whatever
frontmatter conventions a static-site generator, doc indexer, or other tool already
expects. Because the artifact declares `envelope: movie`, validation still needs no
flags.

Every key after `contract` is optional; a minimal artifact carries `contract` alone and
binds its schema some other way (a `--schema` flag, or a host registry in library use).
Contract IDs follow an enforced shape, `[namespace:]Name[/version]`—for example
`example.movies:MoviePage/v1` or `com.acme.docs:IncidentReview/1.0`—naming a payload
contract, not a class or import path.

## Validate

A self-describing artifact validates with no flags; flags override the document when you
need to point a run elsewhere:

```bash
softschema validate doc.md                              # uses the document's bindings
softschema validate doc.md --schema candidate.schema.yaml   # try a different schema
softschema validate doc.md --envelope incident          # designate the payload key
```

`validate` reports structural (JSON Schema) and semantic (Pydantic/Zod model) results
separately as deterministic JSON. Semantic validation loads a model with
`--model module:Class` (Python) or `--model path:export` (Zod)—note that `--model`
imports and executes local code, so use it only with trusted models; a compiled schema
via `--schema` executes nothing and is the safe path for untrusted input.

## Install

Two supported ways to consume softschema; pick by use:

- **Pin it as a dependency** for projects, CI gates, and library use (reproducible,
  fast, offline, and the only way to `import` it):

  ```bash
  uv add --dev softschema==0.2.0        # Python
  npm install -D softschema@0.2.0       # Node (or: bun add -d)
  ```

- **Zero-install** for one-off checks and agent bootstrap:

  ```bash
  uvx softschema@latest --help
  npx softschema@latest --help
  ```

The rule of thumb: if softschema runs more than once, or in CI, or you import it—pin it.
For a quick check or an agent bootstrapping with nothing installed, use a zero-install
runner. See [Installation](docs/installation.md) for details, including the supply-chain
cool-off that makes `@latest` safe to recommend.

## Use as a Library

Both packages expose the same surface (idiomatic per language).
Register contracts at startup and validate at file boundaries:

```python
from pathlib import Path
from softschema import Contract, Contracts, validate_artifact

registry = Contracts()
registry.register(Contract(id="mycorp.docs:IncidentReview/v1", model=IncidentReview,
                           envelope_key="incident"))
result = validate_artifact(Path("incident.md"),
                           contract_id="mycorp.docs:IncidentReview/v1",
                           registry=registry)
```

```ts
import { validateArtifact } from "softschema";

const result = validateArtifact("incident.md", contract);
```

A host registry’s bindings outrank the document’s own (`softschema.schema`/`envelope`),
so a document cannot silently redirect a host’s validation; a contract registered
without a schema path lets self-describing documents bind themselves.
See the [softschema Guide](docs/softschema-guide.md) for the full playbooks.

## Use as an Agent Skill

Both packages ship the same [`SKILL.md`](https://agentskills.io) following the open
Agent Skills standard discovered by Claude Code, Codex, Gemini CLI, Cursor, Copilot, and
~20 other coding agents.
Pointing an agent at the CLI is enough to bootstrap its understanding of the soft-schema
approach: the `--help` epilog routes it to `skill --install`, a brief, and the bundled
docs.

```bash
# Python:
uvx softschema@latest --help            # entry point with skill setup pointers
uvx softschema@latest skill --install   # install repo-local skill mirrors
uvx softschema@latest skill --brief     # compact operating brief
uvx softschema@latest docs guide        # full mental model and adoption path

# TypeScript (same commands, same bundled docs/skill):
npx softschema@latest --help
npx softschema@latest skill --install
npx softschema@latest skill --brief
npx softschema@latest docs guide
```

Self-install the skill into a project so any agent working in the repo finds it natively
(either package writes the identical mirrors):

```bash
uvx softschema@latest skill --install
# or: npx softschema@latest skill --install
# writes:
#   .agents/skills/softschema/SKILL.md   (Codex, Gemini CLI, cross-agent installers)
#   .claude/skills/softschema/SKILL.md   (Claude Code mirror)
```

Both mirrors carry a `DO NOT EDIT` marker.
Re-run `skill --install` to refresh after upgrading the CLI.

## Two Synchronized Implementations

softschema ships **two complete, fully supported implementations** with the same CLI and
library surface:

- **Python / Pydantic**: [`softschema`](docs/softschema-python-design.md) on PyPI (run
  as `softschema` or `softschema-py`).
- **TypeScript / Zod**: [`softschema`](docs/softschema-typescript-design.md) on npm (run
  as `softschema` or `softschema-ts`).

The two are held to **exact behavioral parity**: equivalent CLI inputs, outputs, and
flags; equivalent library APIs; the same canonical compiled JSON Schema
(content-identical, with an equal `schema_sha256` fingerprint); and the same
engine-neutral validation results.
Every behavior change lands in a shared golden-test corpus first, then in both packages,
and CI fails if their outputs or compiled schemas drift.
They release together under the same version number on PyPI and npm.

## Further Reading

- [softschema Guide](docs/softschema-guide.md): the full mental model and adoption
  playbooks.
- [softschema Spec](docs/softschema-spec.md): the exact artifact format and validation
  rules.
- [Movie Page Example](examples/movie_page/README.md): the complete example backing the
  snippets above.
- [Installation](docs/installation.md): pinned vs zero-install, uv and Node setup.

## Development and Contributing

Repo setup, common commands, CI checks, the parity process, and the release workflow
live in [Development](docs/development.md).
The Python and TypeScript implementations must be kept in exact sync: any behavior
change goes through the shared golden corpus first and then lands in both packages.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
