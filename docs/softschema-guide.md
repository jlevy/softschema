# softschema Guide

A soft schema adds structure to a document only when a real consumer needs it.
softschema applies that practice to Markdown/frontmatter and pure YAML: YAML carries
authoritative machine-readable values, while Markdown prose remains inert and free to
carry context, judgment, and explanation.

This guide covers adoption and day-to-day use.
The [Spec](softschema-spec.md) defines exact language-neutral behavior, the
[Library API](api.md) shows Python and TypeScript integration, and the
[runtime design references](#implementation-and-project-references) explain package
internals.

## Quick Start

The pinned commands use the latest published stable release and print their own
compatible example inputs:

<!-- BEGIN SOFTSCHEMA CLAIM guide-python-pin -->
```bash
uvx --from 'softschema==0.2.2' softschema docs example-artifact > report.md
uvx --from 'softschema==0.2.2' softschema docs example-schema > report.schema.yaml
uvx --from 'softschema==0.2.2' softschema validate report.md
```
<!-- END SOFTSCHEMA CLAIM guide-python-pin -->

<!-- BEGIN SOFTSCHEMA CLAIM guide-npm-pin -->
```bash
npx --yes softschema@0.2.2 docs example-artifact > report.md
npx --yes softschema@0.2.2 docs example-schema > report.schema.yaml
npx --yes softschema@0.2.2 validate report.md
```
<!-- END SOFTSCHEMA CLAIM guide-npm-pin -->

This source branch documents an unreleased 0.3 candidate.
See [Migrating to 0.3](migration-0.3.md) before applying source-branch behavior to a
published 0.2 installation.

For an agent, start at the same capability-aware help path:

> Run one exact-pinned `softschema --help` command above, then follow its instructions
> to inspect capabilities and preview a project skill install.

## When a Soft Schema Fits

Use softschema when:

- a human or agent writes an artifact that should remain readable as a document;
- code, QA, aggregation, or another agent consumes specific values from it; and
- the boundary between prose and structured values will evolve.

A common case is an artifact passed between workflow steps.
One step contributes narrative context; the next step consumes a few identifiers,
statuses, measurements, or decisions.
Keeping both in one reviewable file avoids a second data store while letting the handoff
fail clearly when consumed values are missing or malformed.

Use something simpler when:

- no downstream consumer reads structured values: ordinary Markdown conventions are
  enough;
- the artifact is already pure data and needs none of softschema’s identity, metadata,
  or result conventions: use JSON Schema directly; or
- the shape changes on every instance: leave it as prose until a stable consumer
  boundary appears.

The usual progression is:

```text
prose
  -> expected headings and vocabulary
  -> YAML for the few consumed values
  -> schema validation at file boundaries
  -> stricter validation as the contract settles
  -> pure data when useful prose no longer remains
```

Stop wherever the artifact remains useful.
A document can stay in the middle for its entire life.

## The Source-of-Truth Rule

Every consumed value belongs in YAML. The Markdown body may repeat or interpret that
value for readers, but tools must not scrape the body, tables, headings, or generated
prose for structured fields.

```markdown
---
softschema:
  contract: example.movies:MoviePage/v1
  schema: movie-page.schema.yaml
  envelope: movie
  status: enforced
movie:
  title: Spirited Away
  release_year: 2001
  runtime_minutes: 125
  directors:
    - Hayao Miyazaki
  genres: [Animation, Adventure, Family]
---
# Spirited Away (2001)

Hayao Miyazaki's animated fantasy follows Chihiro into a spirit world. It won the 2003
Academy Award for Best Animated Feature.
```

The `movie` mapping is the payload.
The Academy Award belongs only to the narrative because no consumer needs it as data.
A future consumer can promote that fact into YAML without rewriting the rest of the
document.

The `softschema` block describes the artifact:

- `contract` names the payload contract.
- `schema` binds a compiled JSON Schema relative to the artifact.
- `envelope` identifies the top-level payload key.
- `status` selects `soft`, `permissive`, or `enforced` validation.
- `extensions` may hold namespaced portable data.
  It never loads code or changes core validation.

Only `contract` is required in a metadata mapping.
A host registry or explicit CLI flags may supply the other bindings.
Additional top-level keys such as a site generator’s `title` or `tags` remain outside
the selected envelope and are not interpreted by softschema.

## Artifact Profiles

Profiles select storage shape, not contract semantics.

### Markdown With Frontmatter

`frontmatter-md` is the default.
YAML between the opening and closing delimiters holds metadata and payload; everything
after the delimiter is inert Markdown.

```bash
softschema validate report.md
```

### Pure YAML

Use `pure-yaml` explicitly when no Markdown body remains.
A filename suffix never selects it:

```yaml
softschema:
  contract: example.movies:MoviePage/v1
  schema: movie-page.schema.yaml
  status: enforced
title: Spirited Away
release_year: 2001
directors:
  - Hayao Miyazaki
```

```bash
softschema validate report.yaml --profile pure-yaml
```

The root `softschema` mapping is metadata.
Without an explicit envelope, every other root key is the payload.
With `softschema.envelope`, the named key is the payload just as in frontmatter.

## Portable Values

Both runtimes accept the same bounded JSON-compatible YAML domain:

- mappings with string keys, arrays, strings, booleans, null, and finite binary64
  numbers;
- mathematically integral values only within the inclusive JavaScript safe-integer
  range; and
- ordinary Unicode scalar values, subject to byte, node, depth, resource, and scalar
  budgets.

Duplicate keys, non-string keys, aliases, merge keys, custom tags, cycles, non-finite
numbers, unsafe integral values, and invalid Unicode scalars fail before they can become
ordinary runtime objects.
Date- and timestamp-looking YAML 1.2 Core scalars remain strings.
Numeric negative zero normalizes to ordinary zero.

These are parser and security boundaries, so they apply to both artifact-format
grammars. The [Spec](softschema-spec.md#portable-yaml-value-domain) gives exact limits,
numeric rules, and failure shapes.

## Contract and Schema Identity

A contract ID names a payload contract, not an implementation or URI. Recommended form:
`namespace:UpperCamelCaseName/version`.

- `example.movies:MoviePage/v1`
- `mycorp.runbooks:IncidentReview/v2`
- `com.example.docs:DecisionRecord/1.0`

Use `example.*` only in examples, a stable project namespace internally, and reverse DNS
when contracts cross organizations.
Bump the contract version when existing consumers cannot accept the new payload shape.

JSON Schema resource identity is separate.
A compiler stores the logical ID in `x-softschema.contract` and emits `$id` only when
the caller supplies a canonical HTTPS or URN `schema_id`/`schemaId`. This prevents a
convenient class-like contract name from silently becoming a reference base.

Validation resolves fragments and already-loaded explicit resources.
It never fetches HTTP, file, or relative schema resources.
A URI identifies data; it does not grant I/O.

## Adopt One Existing Artifact

Start with a single document family:

1. Identify the values a downstream consumer actually reads.
2. Put those values, and only those values, in one YAML payload mapping.
3. Add a stable `softschema.contract` and select the payload envelope.
4. Start at `soft` when the binding is only descriptive, or `permissive` when known
   fields should validate while unknown fields remain allowed.
5. Bind a reviewed compiled schema or trusted source model.
6. Validate at the file boundary and feed structured failures back to the author.
7. Move to `enforced` only when unknown fields represent bugs.

Before:

```markdown
# Incident 2026-04-12: search latency spike

Affected service: search-api
Severity: SEV-2
Duration: 38 minutes

## Summary
...
```

After:

```markdown
---
softschema:
  contract: example.operations:IncidentReview/v1
  envelope: incident
  status: permissive
incident:
  id: 2026-04-12-search-latency
  affected_service: search-api
  severity: SEV-2
  duration_minutes: 38
---
# Incident 2026-04-12: search latency spike

## Summary
...
```

The consumer now reads `incident.affected_service`. The summary remains prose.

## Decide What Belongs in YAML

Promote a field when all three are true:

1. a consumer reads it;
2. its type and meaning are stable enough to name; and
3. emitting it is more reliable than parsing prose.

Keep background, reasoning, uncertainty, alternatives, and unconsumed detail in prose.
Avoid adding a contract block as decoration to documents nobody validates.

Use **inline-small, companion-large** as a review heuristic.
A few dozen fields or small nested objects fit in frontmatter.
Large machine-generated arrays or results usually belong in a companion YAML/JSON file
resolved by the host before `validate_values`. softschema deliberately has no generic
companion-data loader or resolver DSL.

## Define a Contract in Python or TypeScript

The complete movie example keeps equivalent source models side by side.
Both compile to the same canonical schema and hash.

### Python and Pydantic

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

class IncidentReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    affected_service: str
    severity: Literal["SEV-1", "SEV-2", "SEV-3"]
    duration_minutes: int = Field(ge=0)
```

```bash
softschema-py compile package.incident:IncidentReview \
  --contract example.operations:IncidentReview/v1 \
  --schema-id https://example.com/schemas/incident-review/v1 \
  --out incident-review.schema.yaml
```

### TypeScript and Zod

```ts
import { z } from "zod";

export const IncidentReview = z.strictObject({
  id: z.string(),
  affected_service: z.string(),
  severity: z.enum(["SEV-1", "SEV-2", "SEV-3"]),
  duration_minutes: z.int().min(0),
});
```

Under Node, compile the model to `.js` or `.mjs` first.
Bun may load direct `.ts`:

```bash
bunx --bun softschema compile ./incident.ts:IncidentReview \
  --contract example.operations:IncidentReview/v1 \
  --schema-id https://example.com/schemas/incident-review/v1 \
  --out incident-review.schema.yaml
```

Model compilation and `--model` validation import and execute local code.
Use them only for trusted source.
A compiled schema validates untrusted artifacts without executing a Pydantic or Zod
module.

## Integrate With a Host

Application code owns contract bindings.
Artifact metadata is a fallback and cannot silently redirect a complete host contract.

### Python

```python
from pathlib import Path

from softschema import Contract, Contracts, SchemaStatus
from softschema.runtime import validate_artifact

CONTRACT_ID = "example.operations:IncidentReview/v1"
registry = Contracts()
registry.register(
    Contract(
        id=CONTRACT_ID,
        model=IncidentReview,
        envelope_key="incident",
        status=SchemaStatus.enforced,
        schema_path=Path("incident-review.schema.yaml"),
    )
)
result = validate_artifact(path, contract_id=CONTRACT_ID, registry=registry)
```

### TypeScript

```ts
import { defineContractDescriptor } from "softschema/core";
import { bindContract, validateArtifact } from "softschema/node";

const descriptor = defineContractDescriptor({
  id: "example.operations:IncidentReview/v1",
  model: "./incident.js:IncidentReview",
  envelopeKey: "incident",
  status: "enforced",
  profile: "frontmatter-md",
  schemaPath: "incident-review.schema.yaml",
});
const contract = bindContract(descriptor, IncidentReview);
const result = validateArtifact("incident.md", contract);
```

For values produced by a different trusted parser, call `validate_values` or
`validateValues`. See the [Library API](api.md) for offline resources, portable-core
imports, limits, and result types.

## Validate Collections and CI

When discovery classifies one single explicit path as a regular file, JSON keeps the
legacy single-result contract, including when a later read fails:

```bash
softschema validate docs/incidents/2026-04-12.md
```

For compatibility, one explicit missing path or broken symlink also keeps the legacy
`input_error/not_found` record.
Other discovery-input failures, including a FIFO, an unsafe symlink target, or a
directory without `--recursive`, select a diagnostic-v1 aggregate even when it contains
one input record.

Multiple operands or directory discovery also select diagnostic-v1. One profile applies
to the whole invocation:

```bash
softschema validate docs/incidents --recursive --profile frontmatter-md
softschema validate data --recursive --profile pure-yaml --format jsonl
softschema validate docs --recursive --include '**/*.md' --exclude 'archive/**'
softschema validate docs --recursive --format sarif > softschema.sarif
```

Directory discovery is deterministic, skips discovered symlinks, deduplicates canonical
file identities, and reports a no-match input error rather than a false green run.
Includes and excludes are operand-relative, case-sensitive portable globs and require
`--recursive`. The profile bounds fixed chunks, pattern count, aggregate token
complexity, traversal depth, and invocation-wide match fuel.
A statically oversized pattern request is an invocation error; dynamic fuel exhaustion
is a deterministic discovery-limit input result rather than a partial selection.

Exit precedence is stable:

- 2 if any input cannot be selected or read;
- otherwise 1 if any readable artifact fails parsing or validation; and
- otherwise 0.

Processing continues so JSON, JSONL, and SARIF report partial success honestly.
JSONL contains one self-contained result per line and no summary line.

In CI, pin the package in the project’s lockfile and check three boundaries:

```bash
# Compiled model and committed schema still agree.
softschema-py compile package.incident:IncidentReview \
  --contract example.operations:IncidentReview/v1 \
  --out incident-review.schema.yaml --check

# Every artifact validates in one deterministic invocation.
softschema validate docs/incidents --recursive --profile frontmatter-md

# Generated reader-facing schema projections have not drifted.
softschema generate docs/incident-template.md --check
```

## Generate Reader-Facing Schema Sections

When a runbook table or vocabulary duplicates a schema, place it inside a generated
section:

```markdown
<!-- softschema:generated kind="enum_table" schema="incident-review.schema.yaml" -->

| Field | Allowed values |
| --- | --- |
| `severity` | SEV-1, SEV-2, SEV-3 |

<!-- /softschema:generated -->
```

`softschema generate file.md` updates the section; `--check` reports drift without
writing. Supported projections are `enum_table`, `field_list`, and a pointer-selected
`vocab`. The [Movie Page Example](../examples/movie_page/README.md) contains a live
generated enum table.

## Use softschema With Coding Agents

Install the portable routing skill only after reviewing its target plan:

```bash
softschema doctor --json
softschema skill --install --project --dry-run --text
softschema skill --install --project --text
softschema skill --brief
softschema docs --list --json
```

The installer inspects each target and its stage/backup recovery files through a stable
regular-file descriptor with a shared 1 MiB ceiling.
An oversized, symlinked, or replaced node is a non-mutating conflict in both Python and
TypeScript, including during `--dry-run`. Installer lock records have a separate 4 KiB
ceiling; an oversized, redirected, raced, non-UTF-8, or malformed lock remains active
and blocks mutation.

The skill teaches three jobs and routes details to the CLI:

- author a contract or artifact;
- validate or consume an artifact; and
- change softschema itself using the repository’s golden-first parity process.

Tell an authoring agent the source-of-truth rule explicitly and validate immediately
after it writes. Structured reason codes and source positions are more actionable than a
free-text request to “fix the document.”

See [Coding-Agent Compatibility](agent-compatibility.md) for Codex, Claude Code, Gemini
CLI, GitHub Copilot, Cursor, Windsurf, OpenCode, Aider, Cline, and Roo Code paths,
evidence labels, imports, and scope rules.

## Trust the Processing Stage, Not the File Extension

- Parsing a bounded softschema YAML payload is an inert data operation.
- Validating a reviewed compiled schema performs no retrieval or model execution.
- Loading a Pydantic or Zod model executes trusted local code.
- Rendering MDX/Markdoc, executing notebook cells, or running a configuration language
  belongs to a separate host and trust boundary.
- Installing an Agent Skill changes executable influence for future agent sessions and
  requires ownership and scope review.

See [Security](../SECURITY.md) for the full boundary and the published 0.2.2
limitations.

## Relationship to Adjacent Systems

softschema owns a narrow layer: **strict values, inert prose, portable schema**.

- Astro collections and Contentlayer own application content pipelines and generated
  data APIs.
- MDX, Markdoc, and Jupyter own body syntax, rendering, or execution.
- CUE, Dhall, Nickel, and Pkl own configuration evaluation, composition, and imports.

Those systems offer useful ideas—typed access, editor feedback, positioned diagnostics,
offline bundles, and integrity policies—but replacing softschema’s contract with any one
framework or evaluator would weaken language neutrality.
Integrations should be thin adapters that produce JSON-compatible values before body
execution, not new core syntax or implicit resolvers.

The dated
[adjacent-systems research](project/research/research-2026-07-09-adjacent-schema-document-systems.md)
compares authoring ergonomics, prose fidelity, contract portability, execution risk,
tooling, agent use, migration cost, and offline behavior using primary sources.

## Language-Neutral Conformance

The root `conformance/` source kit lets a third implementation validate schemas,
vectors, digests, offline bundles, and expected results without importing Pydantic or
Zod. The official adapters execute it under Python, Node, and Bun:

```bash
uv run --locked --no-sync python conformance/run.py --check-only
uv run --locked --no-sync python conformance/run.py --implementation all
```

The standard-library consumer verifies an extracted release archive, whose exact
inventory intentionally excludes source-only fixtures and build support files:

```bash
mkdir -p extracted-kit
tar -xf conformance-kit.tar.gz -C extracted-kit
cd extracted-kit
python conformance/consumer.py --json
```

Source schemas intentionally keep `urn:softschema:draft:*` identifiers.
The HTTPS namespace recorded in the manifest is a publication target, not a live
contract, until static hosting returns the exact candidate bytes with verified content
type and digest.
Consumers of the source candidate should use the local manifest and lock
data.

## Common Mistakes

- **Scraping the body:** readers may edit prose or tables without changing the payload.
- **Structuring unconsumed detail:** a field without a consumer adds authoring cost but
  no reliability.
- **Hardening too early:** start permissive and enforce only after unknown fields mean
  bugs rather than exploration.
- **Confusing identities:** `softschema.contract`, `softschema.schema`, and JSON Schema
  `$id` answer different questions.
- **Inferring a profile from a suffix:** always select `pure-yaml` explicitly.
- **Trusting a model path:** model imports execute code; schema-only validation does
  not.
- **Adding hidden retrieval:** remote schemas and configuration imports need an explicit
  policy outside the core validator.
- **Guessing agent paths:** use documented targets and dry-run instead of writing every
  directory a product might scan.

## Implementation and Project References

- [Spec](softschema-spec.md): exact artifact grammar, profiles, portable values,
  metadata, schema policy, diagnostics, and compatibility
- [Library API](api.md): paired public entrypoints and examples
- [Python Design](softschema-python-design.md): modules, adapters, Pydantic, and CLI
- [TypeScript Design](softschema-typescript-design.md): core/Node split, Zod bindings,
  model policy, and result types
- [Movie Page Example](../examples/movie_page/README.md): complete paired source
- [Installation](installation.md): dependency and zero-install choices
- [Migrating to 0.3](migration-0.3.md), [Security](../SECURITY.md), and
  [Changelog](../CHANGELOG.md): compatibility and release context
- [Development](development.md): golden-first parity and repository checks

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
