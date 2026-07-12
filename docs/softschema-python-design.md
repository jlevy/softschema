# softschema Python Design

The broader soft schema practice is explained in [softschema Guide](softschema-guide.md)
and specified in [softschema Spec](softschema-spec.md).

This document covers the Python package that implements the Markdown/YAML validation
slice of that practice.
It is the Python-specific design reference; the guide and spec remain language neutral.

`softschema` owns Python contracts for schema-bound Markdown and YAML artifacts.
Host packages own process orchestration, plugin loading, browser views, repair loops,
provider adapters, and domain models.

The package does not model process graphs or emit structure reports.
A host framework may build those reports by walking its own workflows and resolving
`Contract` objects, but that report shape is application-specific and stays outside the
core package.

## Public Modules

| Module | Purpose |
| --- | --- |
| `softschema.models` | Contract, metadata, status, profile, and warning models |
| `softschema.registry` | In-memory collection that resolves contracts by id |
| `softschema.validate` | Envelope resolution, structural validation, semantic validation, and artifact validation |
| `softschema.canonicalize` | Canonical JSON Schema profile shared with the TypeScript port |
| `softschema.errors` | Engine-neutral structural error records and message templates |
| `softschema.compile` | Pydantic-to-JSON-Schema compilation |
| `softschema.cli` | Small command-line wrapper over the library |

The package root re-exports the common API:

```python
from softschema import Contract, Contracts, compile_model, validate_artifact
```

## Documentation Structure

The docs have two primary entry points:

| Document | Purpose |
| --- | --- |
| [softschema Guide](softschema-guide.md) | Standalone conceptual reference for humans and agents |
| [softschema Spec](softschema-spec.md) | Exact language-neutral artifact format |

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

## Contract Semantics

A `Contract` carries everything the validator needs to handle one artifact contract:

- `id`: stable contract id
- `model`: optional Pydantic model for semantic validation
- `envelope_key`: expected top-level payload key for normal artifacts
- `status`: `soft`, `permissive`, or `enforced`
- `profile`: storage profile such as `frontmatter-md` or `pure-yaml`
- `schema_path`: optional compiled JSON Schema

`Contracts` holds a collection of registered contracts, keyed by `id`. It does not
expose aliases, compatibility maps, or incremental registration helpers.

`SchemaMetadata` represents the document-level `softschema:` block (the self-description
quartet). Fields:

- `contract_id` (alias `contract`): the contract ID (required).
- `schema_ref` (alias `schema`): optional relative path to the compiled schema.
- `envelope`: optional declared envelope key.
- `status`: optional validation strictness (`soft`, `permissive`, `enforced`).

Serialized as `{contract, envelope, schema, status}` (the alias names).
`parse_schema_metadata` accepts both the compact string form (contract ID only) and the
expanded mapping.

## CLI Resolution

The CLI reads `softschema.contract`, `softschema.status`, and a single top-level
envelope key from the artifact by default.
`--contract`, `--status`, and `--envelope` are override and disambiguation flags.

**Schema precedence** (host over document): `--schema` flag > registry
`Contract.schema_path` (library only) > `softschema.schema` (document metadata) >
metadata-only (no structural validation).

**Envelope precedence**: `--envelope` flag > registry `envelope_key` >
`softschema.envelope` (document metadata) > single-key inference (the single
non-`softschema` top-level key; zero or several candidates are rejected as
`envelope_missing` / `envelope_ambiguous`).

Document-declared `schema` paths are relative-only, resolved from the document’s
directory, bounded to the document directory and the current working directory.
Absolute paths and paths that escape both bounds are rejected as `schema_missing`.
Absolute paths require `--schema`.

Without `--model` or `--schema`, and when neither the registry nor the document binds a
schema, `validate` performs a metadata-only check: the frontmatter parses, the
`softschema:` block is well-formed (unknown keys and a malformed contract are errors),
and the envelope resolves; the structural and semantic layers are reported as skipped.
This makes the CLI useful from the `soft` stage, before any schema or model exists.
Passing `--model` or `--schema` adds the corresponding validation layers.

`softschema docs` and `softschema skill` are informational commands.
They print bundled Markdown resources to stdout so agents in installed environments can
discover the guide, spec, skill, and copyable examples without knowing the source
checkout layout. `softschema docs --list --json` exposes the same topic directory as
structured data for automation.

## Validation

The artifact format is language neutral.
The Python package validates at two layers:

- Structural validation with a compiled JSON Schema YAML file
- Semantic validation with a Pydantic model

Pydantic can express Python-only invariants.
JSON Schema carries the portable structural subset that another implementation can
reuse.

```python
from softschema import Contract, SchemaStatus, validate_artifact

contract = Contract(
    id="example.movies:MoviePage/v1",
    model=MoviePage,
    envelope_key="movie",
    status=SchemaStatus.enforced,
)

result = validate_artifact("examples/movie_page/spirited-away.md", contract=contract)
```

Validation fails on malformed frontmatter, invalid `softschema:` metadata, missing
envelopes, missing compiled schemas, JSON Schema errors, and Pydantic errors.

When the contract’s status is `enforced`, structural validation applies the
strict-extras overlay (`apply_enforced_extras` in `softschema.canonicalize`): object
schemas that declare `properties` but omit `additionalProperties` are validated as
`additionalProperties: false`, an explicit `additionalProperties` always wins, and
free-form mappings are unaffected.
The overlay is validation-time only; compiled schemas never change.
`validate_structural` exposes the same behavior via its `strict_extras` keyword.

There are two public entry points: `validate_artifact` (above) for Markdown/YAML
documents, and `validate_values` for an already-extracted mapping (a body-form runtime,
a structured-output adapter, a fixture).
The envelope is resolved directly from the document: an explicit `envelope_key`, or the
single non-`softschema` top-level key when none is given (zero or several candidates are
rejected as `envelope_missing` / `envelope_ambiguous`, per the spec).
`infer_envelope_key` and `EnvelopeAmbiguityError` expose the same inference to callers,
and the CLI’s `--envelope` handling delegates to them.
There is no separate value-path resolver.
A relative `schema_path` is resolved against only the document directory and the current
working directory, so resolution is predictable and never binds to an unrelated compiled
schema in a parent directory.

### Engine-Neutral Structural Errors

Structural validation runs through `jsonschema`, but the error records it returns are
synthesized by softschema, not passed through from the library.
Each violation becomes
`{kind: "schema_violation", path, validator, validator_value, value, message}` where
`message` comes from a shared template keyed on the JSON Schema keyword
(`softschema.errors`). Records are sorted by `(path, validator)`. The TypeScript port
returns the same structured meaning through `ajv`; semantic model errors remain
implementation-specific.

`ArtifactValidationResult.outcome` is the stable boundary discriminator: `valid`,
`invalid`, or `input_error`. The CLI maps those outcomes to exits `0`, `1`, and `2`.

### Alignment with `python-cli-patterns`

The CLI follows the house Python-CLI conventions: exit codes `0` success / `1`
validation failure or drift / `2` usage error; structured data to stdout and diagnostics
to stderr; the package version comes from `importlib.metadata` via
`uv-dynamic-versioning`. The package installs two console scripts, `softschema` and
`softschema-py` (the latter pairs with `softschema-ts` in the shared golden corpus).

### Skill Resource and Mirrors

`skills/softschema/SKILL.md` is the source skill.
An explicit install writes the selected generated copies:

```bash
softschema skill --install --scope project --agent portable --agent claude
```

Project scope writes `.agents/skills/softschema/SKILL.md` and/or
`.claude/skills/softschema/SKILL.md`; personal scope writes the corresponding agent
directory under the user home.
`--dry-run` previews without writing.

The project intentionally uses generated copies rather than symlinks because agent
discovery paths and package registries do not share one portable symlink model.
Full copies are also easier for users and agents to inspect after installation.
The mirrors carry a `DO NOT EDIT` marker and source digest and are regenerated from the
source skill; the drift test verifies the managed wrapper and source payload.

When adding another agent target, extend `SKILL_INSTALL_TARGETS`, regenerate from the
source skill, and update the drift test for the new managed target.

## Warning Codes

Non-fatal advisory issues surface as `SchemaWarning` entries on
`ArtifactValidationResult.warnings`. Every code is enumerated in the public
`WarningCode` enum and uses the `document-*` prefix, so downstream consumers can filter
the family with a single check:

```python
from softschema import WarningCode

if any(w.code.startswith("document-") for w in result.warnings):
    ...
```

| Code | When it’s emitted |
| --- | --- |
| `document-contract-mismatch` | Document declares a `softschema.contract` that doesn’t match the registered contract’s `id`, and the validator is running in advisory metadata mode. In enforced mode (the default) this is a structural error instead, with kind `document_contract_mismatch`. |
| `document-status-mismatch` | Document declares a `softschema.status` that doesn’t match the contract’s status. Always advisory: the contract’s resolved status, not the document’s claim, governs validation (including the `enforced` strict-extras overlay). |

A regression test (`tests/test_warning_codes.py`) holds the table to the enum: any new
emitted code that isn’t a `WarningCode` member fails CI.

### Structural Error Kinds

`StructuralResult.errors[*].kind` uses a separate `snake_case` namespace because errors
are blocking, not advisory.
The current first-release kinds:

| Kind | Meaning |
| --- | --- |
| `artifact_unreadable` | The artifact cannot be opened. |
| `artifact_invalid_utf8` | The artifact is not valid UTF-8. |
| `artifact_too_large` | The artifact exceeds the bounded input size. |
| `yaml_parse_error` | YAML or frontmatter could not be parsed. |
| `no_frontmatter` | Frontmatter block is missing in a Markdown artifact. |
| `frontmatter_not_mapping` | Frontmatter parsed but is not a mapping at the top level. |
| `yaml_not_mapping` | Pure-YAML artifact root is not a mapping. |
| `contract_unknown` | No contract registered for the requested contract ID. |
| `envelope_mismatch` | The contract’s `envelope_key` is not present in the frontmatter. |
| `envelope_ambiguous` | No `envelope_key` and multiple top-level non-`softschema` keys; the envelope must be designated explicitly. |
| `envelope_missing` | No `envelope_key` and zero non-`softschema` top-level keys (frontmatter-md only). |
| `envelope_not_mapping` | The resolved envelope value is present but is not a mapping. |
| `document_softschema_invalid` | `softschema:` metadata block is malformed (unknown keys, bad shape, invalid `contract`). |
| `document_contract_mismatch` | Document’s `softschema.contract` does not match the registered contract’s `id` (enforced metadata mode). |
| `schema_missing` | A compiled schema is bound (a `schema_path` or `softschema.schema`) but the file does not exist, is unreadable, or fails bounded resolution (absolute path or path escaping the document directory and working directory). |
| `schema_invalid` | The bound file is not a valid compiled schema (for example a non-mapping YAML root). |
| `schema_violation` | A JSON Schema validation error (engine-neutral; see Engine-neutral structural errors above). |

Structural error kinds are stable but do not currently carry a public enum; treat them
as the documented surface and open an issue if a consumer needs a typed constant.

## Schema Generation

`softschema compile` emits JSON Schema as YAML:

```bash
softschema compile examples.movie_page.model:MoviePage \
  --contract example.movies:MoviePage/v1 \
  --out examples/movie_page/movie-page.schema.yaml
```

The emitted schema includes:

- `$schema` for JSON Schema 2020-12
- `$id` only when the separate optional `--schema-id` resource URI is supplied
- an `x-softschema` annotation block with `contract` and `schema_sha256` (a
  deterministic SHA-256 over the canonical JSON form of the schema).
  The block is deliberately language-neutral; it carries no `generated_from` provenance,
  since a Pydantic/Zod import path would leak the implementation and break the
  cross-language content identity and equal `schema_sha256`.

Before hashing and serialization, the raw `model_json_schema()` output is run through
`softschema.canonicalize.canonicalize_json_schema`, which preserves annotations,
normalizes an exact nullable `oneOf` to `anyOf`, sorts the set-like `required` array,
and removes only documented Zod/Pydantic representation differences.
This is the canonical JSON Schema profile: a schema compiled from a Pydantic model and
one compiled from the equivalent Zod schema converge to the same canonical schema
content with an equal `schema_sha256` (the hashed canonical JSON is byte-identical; the
YAML serialization bytes may differ).

`x-softschema` is annotation metadata, not a second validation language.
Implementation-specific invariants belong in Pydantic for Python and in Zod refinements
for the TypeScript package.

### Field Annotations (`SoftField`)

`SoftField` is a thin wrapper over Pydantic’s `Field` that records per-field authoring
metadata under `json_schema_extra`. The compiler propagates that block verbatim into the
compiled JSON Schema as a per-property `x-softschema:` block; the runtime never reads it
for validation.

`SoftField` is optional.
Reach for it per field, only when a specific downstream consumer reads a specific
metadata key. A model whose only consumer is `validate_artifact()` should stay on plain
`Field`; the metadata would land in the compiled schema with no reader.
Blanket-annotating every field with `SoftField` ahead of any consumer is per-field
clutter that never pays back.
The movie example annotates only `genres` (one field of ten) for that reason.

```python
from softschema import SoftField

genres: list[str] = SoftField(
    description="Genre labels for the film.",
    group="taxonomy",
    owner="agent",
    tier="constrained",
    instruction="Pick from the standard IMDb genre vocabulary; at least one.",
    min_length=1,
)
```

Recognized keys:

| Key | Type | Meaning |
| --- | --- | --- |
| `group` | `str` | Authoring group label; used to filter generated sections and to bucket QA. |
| `order` | `int` | Display order within a group. |
| `tier` | `hard_fact` / `constrained` / `narrative` | How rigorously reviewers and QA should treat the field. |
| `owner` | `agent` / `postprocess` / `system` / `human` | Who or what produces the value at runtime. Default `agent`. |
| `instruction` | `str` | Short directive aimed at the agent that fills the field. |
| `examples` | `list[Any]` | Example values for prompts and documentation. Omitted from the compiled schema when empty. |
| `aliases` | `dict[str, list[str]]` | Controlled-vocabulary repair table. Omitted when empty. |
| `repair` | `none` / `safe_coerce` / `suggest_alias` | How a future repair pass may handle near-miss values. Default `none`. |

The `SoftOwner`, `SoftTier`, and `RepairKind` `Literal` aliases (also exported from
`softschema`) make typos like `owner="agennt"` fail at type-check rather than at compile
time.

Field constraints (`ge`, `le`, `min_length`, etc.)
flow through the normal Pydantic path; pass them as additional kwargs to `SoftField`.

**When `SoftField` pays off.** Reach for `SoftField` on a field when one of these
consumers exists or is about to be wired:

- A **template generator** that emits section headers from `group` and inline format
  hints from `instruction` and `examples`. Eliminates drift between a hand-maintained
  authoring template and the Pydantic source.
- An **agent prompt builder** that filters by `owner`, so the agent only sees fields it
  owns, with `instruction` text rendered as guidance.
  Postprocess- and system-filled fields stay out of the prompt.
- A **tier-aware QA harness** that routes checks by `tier`: strict equality on
  `hard_fact`, enum or range on `constrained`, LLM-judged review on `narrative`.
- **Generated runbook sections** (`softschema generate`) keyed by `group` for
  `enum_table` and `field_list`, or by a specific pointer for `kind="vocab"`.

When none of those consumers exists or is on the roadmap, leave `Field` alone.
Add `SoftField` annotations field by field as the consumer that reads them lands.

### Schema View

`SchemaView` is the single read-only navigator over a compiled JSON Schema.
Every downstream consumer (QA rules, agent prompts, comparison logic, generated
sections) goes through this one API instead of re-parsing the schema in each module.
That keeps drift out of the readers.

```python
from softschema import SchemaView

view = SchemaView.load(Path("examples/movie_page/movie-page.schema.yaml"))

view.contract_id            # "example.movies:MoviePage/v1"
view.schema_sha256          # 64-char hex digest

view.enum_values("/properties/mpaa_rating")
# ["G", "PG", "PG-13", "R", "NC-17", "NR"]

view.softmeta("/properties/genres")
# {"group": "taxonomy", "tier": "constrained", "owner": "agent", "instruction": "..."}

for field in view.fields_by_group("taxonomy"):
    print(field.name, field.json_type, field.required)
```

`iter_fields()` flattens through `$ref`s into `$defs`, yielding one `FieldInfo` per
leaf-ish field with its JSON Pointer, type, enum (if any), required flag, description,
and `x-softschema` block.
The reader handles Pydantic’s `anyOf: [{$ref: ...}, {type: null}]` shape for
`Foo | None` fields and the `anyOf: [{enum: ...}, {type: null}]` shape for
`Literal[...] | None` fields.

The first release ships the navigator.
`view(name)` (named query presets) and `load_urn` (repo-level URN resolution) are
deferred until a concrete consumer earns them.

Compiled schemas are validation artifacts.
They are distinct from companion data, which stores artifact payload values outside the
Markdown frontmatter.
The first Python release does not implement generic companion-data loading; callers
should keep consumed values in frontmatter unless a host project owns a clearer
companion-data convention.

The package depends on `frontmatter-format` for Markdown frontmatter and YAML reading.
That dependency owns frontmatter mechanics; softschema owns the contract, envelope,
contract, and validation semantics.
Do not treat `frontmatter-format` as a generic softschema companion-data runtime.

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
- Ship Python/Pydantic and TypeScript/Zod as two interchangeable packages held to exact
  behavioral parity (see [TypeScript Package Design](softschema-typescript-design.md)).
- Treat invalid `softschema:` metadata as a validation error.
- Do not carry private compatibility shims into the public repo.
- Bundle guide/spec/example/skill resources into the Python wheel and expose them with
  informational CLI commands.
- Keep examples as copyable source files, not generated scaffolding.

## Deferred

- Companion-data loading beyond compiled JSON Schemas.
- Agent tool APIs beyond the CLI docs and skill instructions.
- `softschema init-example` or other artifact scaffolding commands.
- Generic process graph or structure-report generation.
- Web docs.

## Rejected

- Preserving `legacy` status.
- Preserving alias resolution as public API.
- Making Python class names the required public contract IDs.
- Parsing Markdown body tables as the source of structured values.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
