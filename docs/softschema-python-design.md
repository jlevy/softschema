# Softschema Python Design

The broader soft schema practice is explained in [Softschema Guide](softschema-guide.md)
and specified in [Softschema Spec](softschema-spec.md).

This document covers the Python package that implements the Markdown/YAML validation
slice of that practice.
It is the Python-specific design reference; the guide and spec remain language-neutral.

`softschema` owns Python contracts for schema-bound Markdown and YAML artifacts.
Host packages own process orchestration, plugin loading, browser views, repair loops,
provider adapters, and domain models.

The package does not model process graphs or emit structure reports.
A host framework may build those reports by walking its own workflows and resolving
`SoftschemaBinding` objects, but that report shape is application-specific and stays
outside the core package.

## Public Modules

| Module | Purpose |
| --- | --- |
| `softschema.models` | Binding, metadata, status, profile, stage, and warning models |
| `softschema.registry` | Contract ID to binding resolution |
| `softschema.validate` | Value resolution, structural validation, semantic validation, and artifact validation |
| `softschema.compile` | Pydantic-to-JSON-Schema sidecar compilation |
| `softschema.cli` | Small command-line wrapper over the library |

The package root re-exports the common API:

```python
from softschema import SoftschemaBinding, SoftschemaRegistry, compile_model, validate_artifact
```

## Documentation Structure

The docs have two primary entry points:

| Document | Purpose |
| --- | --- |
| [Softschema Guide](softschema-guide.md) | Standalone conceptual reference for humans and agents |
| [Softschema Spec](softschema-spec.md) | Exact language-neutral artifact format |

The root README is a short subset of the guide.
It should orient a new visitor, show the main example, and point to the guide and spec
rather than repeating their content.

Template workflow docs keep template names: [development.md](development.md),
[installation.md](installation.md), and [publishing.md](publishing.md).
Package design details live in this document unless they grow large enough to justify a
separate reference.

`AGENTS.md` and `skills/softschema/SKILL.md` point agents to the guide first, then the
spec, then the example.
This keeps the agent entry points short while making the repo usable as a transferable
skill.

The CLI also bundles those docs and examples:

```bash
softschema docs --list
softschema docs --list --json
softschema docs guide
softschema docs spec
softschema docs example-artifact
softschema skill --brief
```

This follows the CLI-as-skill pattern: a short skill file can tell an agent which
command to run, and the CLI can print progressively larger reference material only when
needed. Example files remain copyable references.
The CLI does not include an `init-example` or other scaffolding command in the first
release.

## Binding Semantics

`SoftschemaBinding` names one artifact contract:

- `contract_id`: stable contract ID
- `model`: optional Pydantic model for semantic validation
- `envelope_key`: expected top-level payload key for normal artifacts
- `status`: `soft`, `permissive`, or `enforced`
- `profile`: storage profile such as `frontmatter-md` or `pure-yaml`
- `schema_path`: optional generated JSON Schema sidecar

The registry registers complete bindings.
It does not expose aliases, compatibility maps, or incremental registration helpers.

## CLI Resolution

The CLI reads `softschema.contract`, `softschema.status`, and a single top-level
envelope key from the artifact by default.
`--contract`, `--status`, and `--envelope` are override and disambiguation flags.

The CLI still needs a validation implementation, such as `--model` or `--schema`,
because document metadata identifies the contract but does not import code.

`softschema docs` and `softschema skill` are informational commands.
They print bundled Markdown resources to stdout so agents in installed environments can
discover the guide, spec, skill, and copyable examples without knowing the source
checkout layout. `softschema docs --list --json` exposes the same topic directory as
structured data for automation.

## Validation

The artifact format is language-neutral.
The Python package validates at two layers:

- Structural validation with a JSON Schema YAML sidecar
- Semantic validation with a Pydantic model

Pydantic can express Python-only invariants.
JSON Schema carries the portable structural subset that another implementation can
reuse.

```python
from softschema import SoftschemaBinding, SoftschemaStatus, validate_artifact

binding = SoftschemaBinding(
    contract_id="example.movies:MoviePage/v1",
    model=MoviePage,
    envelope_key="movie",
    status=SoftschemaStatus.enforced,
)

result = validate_artifact("examples/movie_page/spirited-away.md", binding=binding)
```

Validation fails on malformed frontmatter, invalid `softschema:` metadata, missing
envelopes, missing schema sidecars, JSON Schema errors, and Pydantic errors.

## Schema Generation

`softschema compile` emits JSON Schema as YAML:

```bash
uv run softschema compile examples.movie_page.model:MoviePage \
  --contract example.movies:MoviePage/v1 \
  --out examples/movie_page/movie-page.schema.yaml
```

The emitted schema includes:

- `$schema` for JSON Schema 2020-12
- `$id` when a contract ID is supplied
- an `x-softschema` annotation block with `contract`, `generated_from`,
  `softschema_format_version`, and `schema_sha256` (a deterministic SHA-256 over the
  canonical JSON form of the schema)

`x-softschema` is annotation metadata, not a second validation language.
Implementation-specific invariants belong in Pydantic for Python and in Zod refinements
for a future TypeScript package.

Schema sidecars are validation artifacts.
They are distinct from data sidecars, which store artifact payload values outside the
Markdown frontmatter.
The first Python release does not implement generic data-sidecar loading; callers should
keep consumed values in frontmatter unless a host project owns a clearer sidecar
convention.

The package depends on `frontmatter-format` for Markdown frontmatter and YAML reading.
That dependency owns frontmatter mechanics; softschema owns the contract, envelope,
binding, and validation semantics.
Do not treat `frontmatter-format` as a generic softschema data-sidecar runtime.

## Dependency Boundary

The standalone package depends only on the packages declared in `pyproject.toml`. It
must not import project-specific frameworks, domain packages, browser packages, GCP
libraries, or process-orchestration code.

Host packages own higher-level inventories such as process graph reports, browser views,
repair workflows, plugin discovery, and generated prompt sections.
`softschema` provides the contract and validation layer those hosts can call at file
boundaries.

## Accepted

- Keep the soft schema mental model and artifact format programming-language agnostic.
- Use `softschema.contract` for the public metadata key.
- Recommend namespace plus UpperCamelCase name plus version for contract IDs.
- Keep the first Python package at the repo root for uv and PyPI simplicity, while
  storing source under `packages/python`.
- Keep TypeScript/Zod as a future path, represented only by a README stub for now.
- Treat invalid `softschema:` metadata as a validation error.
- Do not carry private compatibility shims into the public repo.
- Bundle guide/spec/example/skill resources into the Python wheel and expose them with
  informational CLI commands.
- Keep examples as copyable source files, not generated scaffolding.

## Deferred

- TypeScript/Zod implementation.
- Sidecar data loading beyond simple JSON Schema sidecars.
- Agent tool APIs beyond the CLI docs and skill instructions.
- `softschema init-example` or other artifact scaffolding commands.
- Generic process graph or structure-report generation.
- Web docs.

## Rejected

- Preserving `legacy` status.
- Preserving alias resolution as public API.
- Making Python class names the required public contract IDs.
- Parsing Markdown body tables as the source of structured values.

<!-- This document follows std-doc-guidelines.md.
Review guidelines before editing.
-->
