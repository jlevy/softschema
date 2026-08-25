# softschema

`softschema` applies gradual contracts to Markdown and YAML artifacts.
In Markdown, values a downstream tool reads live in YAML frontmatter under a named
contract; the body remains prose.
Add a field when a consumer needs it, and tighten validation as the shape settles.

Give that rule to a coding agent before it designs a workflow.
It can write each artifact as both readable context and a validated handoff.
Later code and agent steps read named values instead of parsing or reinterpreting prose.

## Quick Start

Try it anywhere, with nothing installed but [uv](https://docs.astral.sh/uv/) or Node.
Print the bundled example artifact and its compiled schema, then validate—the artifact
is fully self-describing, so no flags are needed:

```bash
uvx softschema@latest docs example-artifact > spirited-away.md
uvx softschema@latest docs example-schema > movie-page.schema.yaml
uvx softschema@latest validate spirited-away.md
```

(Or `npx -y softschema@latest ...` for the Node implementation; the two are
interchangeable.)

To set up softschema in a repository with an agent, tell the agent:

> Run `uvx softschema@latest --help` (for the Python implementation) or
> `npx -y softschema@latest --help` (for the Node implementation) and follow the
> instructions to set up softschema for this repo as a skill.

The help output points the agent to the explicit install command, which writes the
portable Agent Skills location and the Claude Code discovery mirror.

## Why Explain Soft Schemas to an Agent?

A coding agent can produce readable Markdown without separating context from values that
a later step must consume.
Without an explicit boundary, those values may appear in prose or tables.
The file remains readable, but every consumer must parse unstable text, and a later
agent session must infer the values again.

The soft-schema convention gives the agent a stable rule.
YAML is authoritative for any value a consumer reads; the body is for reasoning,
evidence, and caveats.
A value moves into YAML only when a consumer needs it, and validation runs where the
artifact passes to that consumer.

Once that boundary is explicit, the same artifacts support:

- **Explicit handoffs.** Later agent steps and ordinary code read named fields under a
  contract instead of guessing at headings or table layouts.
- **Validation-guided repair.** `softschema validate` separates structural and semantic
  failures. Structural records carry stable categories and paths, so an agent can repair
  the named field and retry instead of interpreting free-form feedback.
- **Durable project memory.** Structured values remain queryable across files and
  sessions, while the body preserves why a decision was made.
- **Derived reports.** Code can regenerate indexes, ledgers, and summaries from
  validated payloads instead of maintaining those views as separate sources of truth.
- **Incremental automation.** A workflow can begin as documents, then acquire typed
  fields, validation, aggregations, and CI checks one consumer at a time.

Across a pipeline, each artifact serves as both persistent context and a validated
interface: the body preserves why the work took its current form, and the payload tells
the next step which values it can rely on.

The project skill makes the rule discoverable to agents working in a repository.
The CLI makes it testable: `compile --check` detects drift between a model and its
compiled schema, `generate --check` detects stale generated sections, and the same
compiled contract works with the Python and TypeScript implementations.

## The Convention

**Soft schemas** name the general practice of adding structure to a document as
consumers need it. **softschema** is this repository’s Markdown-and-YAML specification
and the matching CLI and libraries.

A hard schema defines a whole record up front.
A soft schema lets a document begin as prose and adds typed fields as downstream needs
become clear. The validation on a promoted field can be strict; the “soft” part is when
and where structure is introduced.

The default artifact is Markdown with YAML frontmatter.
A payload under one envelope key holds the values a program reads, and a named contract
defines their shape.
The Markdown body holds context, reasoning, and caveats.
It may repeat values for readers, but consumers never parse it as data.

An artifact can move along this spectrum without being rewritten all at once:

```text
plain Markdown prose
  -> frontmatter for the first values a consumer reads
  -> permissive contract validation while the shape is settling
  -> enforced validation against JSON Schema, Pydantic, or Zod
  -> pure structured data if the prose body no longer serves a purpose
```

Promote a value into YAML when a tool reads it, validate it at the boundary when
correctness matters, and tighten enforcement as the shape settles.
Leave everything else as prose.

## Where Soft Schemas Fit

Use a soft schema when a human or agent writes a document and a downstream consumer
needs some, but not all, of its content as data.
Common shapes include:

- **Agent pipeline handoffs.** Put status, identifiers, routing decisions, and output
  paths in frontmatter; keep rationale and caveats in the body.
  An orchestrator or later agent step can validate the handoff before acting on it.
- **Extraction and harmonization.** Put normalized fields and source identifiers in
  frontmatter; keep provenance and source-specific cleanup decisions in prose.
  Aggregation code reads only the validated payload.
- **Research and evaluation loops.** Put measurements, confidence intervals, and a
  constrained verdict in frontmatter; keep the hypothesis and interpretation in prose.
  An acceptance rule and a regenerated ledger consume the structured values.
- **Document-backed application data.** Put fields used by a UI, check, or index in
  frontmatter; keep background and long-form content in the body.
  New fields acquire a contract when a component starts reading them.

If no consumer reads structured values, plain Markdown is enough.
If the artifact is already pure structured data, use its schema directly.
The [guide](docs/softschema-guide.md#when-to-use-it) gives the full adoption criteria.

## Example: Recording a Research Loop

A research loop is any process that repeatedly proposes an idea, measures it, and
decides: optimizing a program, tuning prompts against an eval, comparing libraries.
Each iteration produces a record with two halves that resist a single format: numbers a
tool must read, and reasoning only the author can write.
In the
[performance work that motivated this playbook](https://github.com/jlevy/softschema/pull/33),
each of 51 experiments is one artifact whose enforced frontmatter carries the hypothesis
ID, the host and subject fingerprints, the measured medians with confidence intervals,
and a verdict drawn from a fixed set, while the Markdown body explains what the profiler
suggested, what was tried, and why the numbers meant what they said.
Code reads the YAML to apply the accept rule and regenerate a ledger; humans and agents
read the prose.

- **Negative results survive.** A refuted hypothesis costs one artifact and stays
  queryable, so the ledger can lead with its failures, which are the most reusable part
  of a research record and the part loose session notes never retain.
- **Reports become views.** The ledger is regenerated from validated artifacts, so it
  cannot drift from the record; an artifact that stops matching the contract fails the
  build instead of quietly contributing a wrong row.
- **Agents get durable memory.** A session picking the loop up months later reads back
  what was tried and why it was dropped, without re-running anything.

See
[Playbook: Record a Research Loop](docs/softschema-guide.md#playbook-record-a-research-loop)
for the artifact shape and the four habits that keep the record and the report in sync.

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
When a structural schema is bound, `status: enforced` rejects any property the schema
does not declare. With only a host-supplied Pydantic or Zod model, validation delegates
to that model and does not invent a structural schema; with neither, validation checks
metadata only.

For an ordinary schema—one that declares its fields in one place per object—that is the
whole rule, and the paragraph below is safe to skip.

Two advanced cases need more care: schemas that **compose** declarations across `allOf`,
`anyOf`, `oneOf`, or `$ref`, and **dependent** schemas where one field’s schema depends
on another field’s value (`if`/`then`/`else`, `dependentSchemas`). softschema enforces
those too, at each supported object location, but only where it can do so without
changing what the authored schema otherwise accepts; the spec’s
[support matrix](docs/softschema-spec.md#support-matrix) is the exact boundary.

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

- **Install it as a dependency** for projects, CI gates, and library use (reproducible
  through the project lockfile, fast, offline, and the only way to `import` it):

  ```bash
  uv add --dev softschema               # Python
  npm install -D softschema@latest      # Node (or: bun add -d)
  ```

- **Zero-install** for one-off checks and agent bootstrap:

  ```bash
  uvx softschema@latest --help
  npx -y softschema@latest --help
  ```

The rule of thumb: if softschema runs more than once, or in CI, or you import it—install
it in the project and commit the lockfile.
For a quick check or an agent bootstrapping with nothing installed, use a zero-install
runner.
See [Installation](docs/installation.md) for details and the project supply-chain
policy.

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
Agent Skills standard.
The portable mirror works with agents that discover `.agents`; the optional Claude
mirror supports Claude Code’s discovery path.
Pointing an agent at the CLI is enough to bootstrap its understanding of the soft-schema
approach: the `--help` epilog routes it to `skill --install`, a brief, and the bundled
docs.

```bash
# Python:
uvx softschema@latest --help            # entry point with skill setup pointers
uvx softschema@latest skill --install --scope project --agent portable --agent claude
uvx softschema@latest skill --brief     # compact operating brief
uvx softschema@latest docs guide        # full mental model and adoption path

# TypeScript (same commands, same bundled docs/skill):
npx -y softschema@latest --help
npx -y softschema@latest skill --install --scope project --agent portable --agent claude
npx -y softschema@latest skill --brief
npx -y softschema@latest docs guide
```

Self-install the skill into a project so any agent working in the repo finds it natively
(either package writes the identical mirrors):

```bash
uvx softschema@latest skill --install --scope project --agent portable --agent claude
# or: npx -y softschema@latest skill --install --scope project --agent portable --agent claude
# writes:
#   .agents/skills/softschema/SKILL.md   (Codex, Gemini CLI, cross-agent installers)
#   .claude/skills/softschema/SKILL.md   (Claude Code mirror)
```

Both mirrors carry a `DO NOT EDIT` marker.
Re-run `skill --install` to refresh after upgrading the CLI.

## Two Synchronized Implementations

softschema ships two interchangeable implementations with the same CLI and library
surface:

- **Python / Pydantic**: [`softschema`](docs/softschema-python-design.md) on PyPI (run
  as `softschema` or `softschema-py`).
- **TypeScript / Zod**: [`softschema`](docs/softschema-typescript-design.md) on npm (run
  as `softschema` or `softschema-ts`).

The two share the same commands, exit classes, structured result meaning, canonical
compiled JSON Schema, and `schema_sha256` fingerprint.
Human-readable presentation and model-native errors may differ where the runtime does;
shared vectors and broad CLI journeys keep the portable contract aligned.
They release together under the same version number on PyPI and npm.

## Further Reading

- [softschema Guide](docs/softschema-guide.md): the full mental model and adoption
  playbooks.
- [softschema Spec](docs/softschema-spec.md): the exact artifact format and validation
  rules.
- [Movie Page Example](examples/movie_page/README.md): the complete example backing the
  snippets above.
- [Installation](docs/installation.md): pinned vs zero-install, uv and Node setup.
- [JSON Schema Composition, Field Dependencies, and Undeclared Properties](https://github.com/jlevy/softschema/blob/main/docs/project/research/research-2026-08-23-json-schema-composition-and-enforcement.md):
  advanced background for composed and dependent schemas only; not needed for ordinary
  soft schemas.

## Development and Contributing

Repo setup, common commands, CI checks, the parity process, and the release workflow
live in [Development](docs/development.md).
The Python and TypeScript implementations must be kept in exact sync: any behavior
change goes through the shared golden corpus first and then lands in both packages.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
