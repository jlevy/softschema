# softschema

softschema validates Markdown/frontmatter and pure YAML artifacts without turning their
prose into a programming language or database.

The rule is simple: **put every value a downstream tool consumes in YAML; leave
explanations, judgment, and context as prose.** Name the YAML payload with a contract,
validate it at the boundary, and add structure only when a real consumer needs it.

## Try It

The pinned commands use the latest published stable package.
They print a copyable artifact and its compiled JSON Schema, then validate with no
project setup:

<!-- BEGIN SOFTSCHEMA CLAIM python-pin -->
```bash
uvx --from 'softschema==0.2.2' softschema docs example-artifact > spirited-away.md
uvx --from 'softschema==0.2.2' softschema docs example-schema > movie-page.schema.yaml
uvx --from 'softschema==0.2.2' softschema validate spirited-away.md
```
<!-- END SOFTSCHEMA CLAIM python-pin -->

<!-- BEGIN SOFTSCHEMA CLAIM npm-pin -->
```bash
npx --yes softschema@0.2.2 docs example-artifact > spirited-away.md
npx --yes softschema@0.2.2 docs example-schema > movie-page.schema.yaml
npx --yes softschema@0.2.2 validate spirited-away.md
```
<!-- END SOFTSCHEMA CLAIM npm-pin -->

This development branch contains the unreleased 0.3 behavior described in the
[changelog](CHANGELOG.md) and [migration guide](docs/migration-0.3.md).
A source fix is not an available package update until the release metadata, registries,
and published artifacts are verified.

Release metadata currently reports conformance
<!-- BEGIN SOFTSCHEMA CLAIM conformance-status -->`unavailable`<!-- END SOFTSCHEMA CLAIM conformance-status -->
at version

<!-- BEGIN SOFTSCHEMA CLAIM conformance-version -->`0.0.0-draft.1`<!-- END SOFTSCHEMA CLAIM conformance-version -->.

## Artifact Shape

```markdown
---
softschema:
  format: "1"
  contract: example.movies:MoviePage/v1
  schema: movie-page.schema.yaml
  envelope: movie
  status: enforced
movie:
  title: Spirited Away
  release_year: 2001
  directors: [Hayao Miyazaki]
---
# Spirited Away

Hayao Miyazaki's animated fantasy follows Chihiro into a spirit world. It won the 2003
Academy Award for Best Animated Feature.
```

The `movie` mapping is authoritative structured data.
The body remains inert, reader-facing Markdown; softschema never scrapes its prose or
tables for values. `contract` names the payload contract, not a Python class, TypeScript
export, schema path, or JSON Schema `$id`.

New artifacts use the exact quoted `format: "1"`. Existing artifacts without `format`
use the legacy metadata grammar.
See the [Spec](docs/softschema-spec.md) for exact profiles, limits, identity, reference,
regex, format, extension, and result rules.

## Pick a Runtime

| Runtime | Package and commands | Trusted model source |
| --- | --- | --- |
| Python 3.11+ / Pydantic | PyPI `softschema`; `softschema` or `softschema-py` | `.py` model import |
| Node 22.12+ / Zod | npm `softschema`; `softschema` or `softschema-ts` | built `.js` or `.mjs` |
| Bun 1.3.11+ / Zod | npm `softschema`; `bunx --bun softschema` | `.js`, `.mjs`, or direct `.ts` |

The machine-checked runtime floors are Python

<!-- BEGIN SOFTSCHEMA CLAIM python-minimum -->`3.11`<!-- END SOFTSCHEMA CLAIM python-minimum -->,

Node

<!-- BEGIN SOFTSCHEMA CLAIM node-minimum -->`22.12`<!-- END SOFTSCHEMA CLAIM node-minimum -->,

and Bun

<!-- BEGIN SOFTSCHEMA CLAIM bun-minimum -->`1.3.11`<!-- END SOFTSCHEMA CLAIM bun-minimum -->.

Both implementations use the same artifact contract, CLI behavior, canonical compiled
JSON Schema, normalized results, and conformance vectors.
Library names remain idiomatic: snake_case/Pydantic in Python and camelCase/Zod in
TypeScript.

## Validate Files

```bash
softschema validate report.md
softschema validate report.yaml --profile pure-yaml
softschema validate docs --recursive --profile frontmatter-md --format json
softschema validate data --recursive --profile pure-yaml --format jsonl
softschema validate docs --recursive --format sarif > softschema.sarif
```

`frontmatter-md` is the default.
A `.yaml` or `.yml` suffix never selects `pure-yaml`. One explicit path classified as a
regular file retains legacy JSON even if a later read fails.
Missing paths and broken symlinks keep legacy `not_found`; other discovery failures,
multiple paths, and directory discovery use diagnostic-v1. JSONL emits one
self-contained result per line; SARIF carries source positions for code-scanning tools.

Validation is offline: fragments and already-loaded explicit resources are available,
but a schema URI never authorizes HTTP, file, or implicit relative-path retrieval.
`--model` imports and executes trusted local code.
Use a reviewed compiled schema for untrusted artifacts.

## Use the Libraries

```python
from softschema import Contract, Contracts
from softschema.runtime import validate_artifact

registry = Contracts()
registry.register(Contract(id="example.movies:MoviePage/v1", model=MoviePage,
                           envelope_key="movie", schema_path="movie-page.schema.yaml"))
result = validate_artifact(path, contract_id="example.movies:MoviePage/v1",
                           registry=registry)
```

```ts
import { defineContractDescriptor } from "softschema/core";
import { bindContract, validateArtifact } from "softschema/node";

const descriptor = defineContractDescriptor({
  id: "example.movies:MoviePage/v1", model: "./model.js:MoviePage",
  envelopeKey: "movie", status: "enforced", profile: "frontmatter-md",
  schemaPath: "movie-page.schema.yaml",
});
const result = validateArtifact("report.md", bindContract(descriptor, MoviePage));
```

See the [Library API](docs/api.md) and paired
[Movie Page Example](examples/movie_page/README.md).

## Install the Agent Skill

The portable Agent Skills file is a concise routing layer over the CLI and bundled docs.
Preview project scope and ownership before writing:

```bash
softschema skill --install --project --dry-run --text
softschema skill --install --project --text
```

The default project targets are `.agents/skills/softschema/SKILL.md` and
`.claude/skills/softschema/SKILL.md`. Explicit selectors support nine documented native
skill hosts; Aider uses an explicit read recipe.
Installer reads are bounded and fail closed on unsafe targets, recovery files, or locks.
See [Coding-Agent Compatibility](docs/agent-compatibility.md) for evidence and limits.

## Documentation

- [Guide](docs/softschema-guide.md): mental model, adoption, authoring, validation, CI,
  agents, and alternatives
- [Spec](docs/softschema-spec.md): normative language-neutral behavior
- [Library API](docs/api.md): paired Python and TypeScript integration
- [Python Design](docs/softschema-python-design.md) and
  [TypeScript Design](docs/softschema-typescript-design.md): runtime internals
- [Security](SECURITY.md), [0.3 Migration](docs/migration-0.3.md), and
  [Changelog](CHANGELOG.md): trust, compatibility, and release delta
- [Development](docs/development.md): parity workflow and repository checks

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
