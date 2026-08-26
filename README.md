# softschema

`softschema` applies gradual contracts to YAML data.
The standard profile is Markdown with YAML frontmatter and an optional body.
Pure YAML is also supported when the structured record stands on its own.
Start with a named convention, validate the fields that have stabilized, and make the
compiled schema authoritative once undeclared fields should fail.

This gives agents and software a shared path from loose records to enforced schemas.
The contract can evolve without changing an artifact’s profile or its Markdown body.
When a record needs explanation, Markdown keeps that context next to values software can
read.

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

## Why Give Soft Schemas to an Agent?

A coding agent often has to build a data workflow before the final record shape is
known. A closed schema written too early turns guesses into constraints.
A collection left entirely loose gives later code no stable boundary.

A soft schema gives the agent an iterative method.
It can collect records in YAML, name a contract, add stable fields and constraints as
the records and consumers reveal them, and move the contract from `soft` to `permissive`
to `enforced`. The schema and payload can change without a profile migration.
A Markdown body can stay unchanged, or be absent from the start.

That progression supports:

- **Gradual data modeling.** The agent can formalize the stable core of a record while
  leaving extension fields open until their purpose and type are understood.
- **Agent and software coordination.** Agent steps, scripts, services, QA checks, and
  report generators read the same named payload fields under the same contract.
- **Validation-guided refinement.** `softschema validate` returns structural and
  semantic results. Stable categories and paths let an agent repair a field, revise a
  constraint, or identify an extension that belongs in the schema.
- **Context beside data.** When a record needs provenance, judgment, or caveats that do
  not belong in fixed fields, the Markdown profile keeps that prose next to the YAML
  payload. Consumers still read YAML only.
- **Interoperability with strict systems.** A contract can converge on the fields and
  constraints required by a database, API, or other import boundary.
  Enforced validation rejects incompatible records before the handoff.
- **Derived views and durable memory.** Code can regenerate indexes, ledgers, and
  summaries from validated payloads, while optional prose preserves the reasoning that
  future humans or agents need.

The structured payload is the software interface, and its status states how mature that
boundary is. The optional body supplies local context without forcing software to parse
prose. Together, the two profiles support context engineering alongside database-style
schema development without making prose part of the machine interface.

The project skill makes the rule discoverable to agents working in a repository.
The CLI makes it testable: `compile --check` detects drift between a model and its
compiled schema, `generate --check` detects stale generated sections, and the same
compiled contract works with the Python and TypeScript implementations.

## The Convention

**Soft schemas** name the practice of developing a data contract as the records and
their consumers become better understood.
**softschema** is this repository’s YAML-based artifact specification and the matching
CLI and libraries. Artifact payloads use YAML in both profiles; softschema does not
define a JSON artifact profile.

Two choices are independent:

| Choice | Options | What It Controls |
| --- | --- | --- |
| Artifact profile | `frontmatter-md` or `pure-yaml` | Whether the artifact also carries a Markdown body or consists only of structured data. |
| Contract status | `soft`, `permissive`, or `enforced` | Whether the contract is a convention, validates known fields under authored rules, or makes a bound structural schema authoritative. |

In `pure-yaml`, the document root is the payload after softschema metadata is removed.
In `frontmatter-md`, YAML frontmatter holds the payload and the body holds reader-facing
context. The body may repeat values for readers, but consumers never parse it as data.

The same record family can move through increasing schema maturity without changing its
artifact profile:

```text
loose YAML records
  -> named field conventions                              (soft)
  -> validation for the stable fields                     (permissive)
  -> more fields and constraints as consumers reveal them (permissive)
  -> an authoritative structural boundary                 (enforced)
  -> validation before a database, API, or other strict system
```

At any stage, use Markdown with frontmatter when the record benefits from nearby
explanation, provenance, or review notes.
Use pure YAML when the whole artifact is structured data.
Tightening the schema does not require changing that prose.

## Where Soft Schemas Fit

Use a soft schema when records have a useful but incomplete shape, or when a workflow
needs a controlled path toward a strict downstream boundary.
Common shapes include:

- **Record enhancement and harmonization.** Start with heterogeneous pure YAML records,
  identify recurring fields, normalize them, and expand the contract as each field
  becomes reliable enough for aggregation.
- **Software boundaries.** Let batch jobs, services, QA checks, and report generators
  exchange permissive records while their shared contract develops.
  Enforce it once unknown fields represent integration errors.
- **Database and API staging.** Align a YAML contract with a target system’s required
  fields and constraints, then validate records under `enforced` before import.
- **Agent pipelines.** Give agents the same contract progression while they develop
  producers and consumers together.
  Structured errors make both bad data and premature constraints visible during
  refinement.
- **Context-rich records.** Use the Markdown profile for research results, application
  content, incident records, or decisions that need structured fields plus provenance,
  interpretation, or caveats.

If no downstream consumer reads structured values, no contract is needed.
If the full closed schema is already known and an ordinary validator covers the
workflow, gradual contract maturity may add little.
The [guide](docs/softschema-guide.md#when-to-use-it) gives the full adoption criteria.

## Example: Recording a Research Loop

A research loop is any process that repeatedly proposes an idea, measures it, and
decides: optimizing a program, tuning prompts against an eval, comparing libraries.
This is one case where the Markdown profile fits: each iteration has measurements a tool
must read and interpretation that does not fit fixed fields.
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

## Artifact Profiles

A softschema artifact is either Markdown with YAML frontmatter or pure YAML. Both use
the same contracts and status progression.

The standard example uses `frontmatter-md` because it shows the structured payload and
optional context together.
This profile is usually the better authoring surface when a record needs explanation,
provenance, or review notes.
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

Use `pure-yaml` when the structured record stands on its own.
The whole document root is the payload after the `softschema:` metadata block is
removed:

```yaml
softschema:
  contract: example.records:SourceRecord/v1
  status: soft
source_id: article-1842
title: Example source
language: en
```

This record can acquire a model and move through `permissive` to `enforced` without a
Markdown wrapper.

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
softschema validate incident.md                         # frontmatter Markdown
softschema validate record.yaml                         # pure YAML
softschema validate incident.md --schema candidate.schema.yaml  # override its schema
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
