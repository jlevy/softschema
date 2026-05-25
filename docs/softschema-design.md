# Softschema Design

This is the durable design reference for softschema. It covers the language-neutral
artifact and validation design, the rationale behind the choices, and the Python
implementation that ships in this repository. A TypeScript section is reserved for
future work.

The companion docs serve different purposes:

| Document | Purpose |
| --- | --- |
| [README](../README.md) | First-visitor orientation. |
| [Softschema Guide](softschema-guide.md) | Standalone teaching reference for humans and agents adopting the pattern. |
| [Softschema Spec](softschema-spec.md) | Exact, language-neutral artifact format rules. |
| **Softschema Design (this doc)** | Why the design is the way it is. Implementation references. Roadmap. |

The guide teaches *what* to do; the spec defines *what's valid*; this document explains
*why* and *how it's built*.

## Motivation

### The problem

LLMs and coding agents have made it easy to automate work that still looks like human
reasoning: mixed prose, judgment calls, partial structure, implicit context. That work
gets automated long before it gets *exact* or *structured*. The output of an automated
step can still be ambiguous, inconsistent in shape, and weakly composable with code
downstream of it.

The traditional reflex — "if it's automated, make it code" — over-corrects. A team that
already has a working agent or human-authored workflow loses readability, narrative
context, and review surface when it skips ahead to a pure-data representation. The
practice we want lets a workflow stay human-readable while consumers still get the
structured values they need.

### Three axes, not one

Automation, exactness, and structure are independent axes. A team can move on one
without forcing movement on the others:

| Axis | Low end | High end |
| --- | --- | --- |
| Automation | Human-performed | Harness-driven |
| Exactness | Natural-language judgment | Deterministic validation |
| Structure | Prose and conventions | Typed records or pure data |

Before LLMs, "automated" usually implied code, which implied exact and structured. With
agentic workflows, those equivalences break. Soft schemas are a mechanism for raising
exactness and structure gradually, in step with what consumers actually need, instead of
forcing the whole workflow into one shape.

### The promotion path

```text
prose
  → expected sections and vocabulary
  → YAML/frontmatter values for consumed fields
  → schema validation at boundaries
  → pure data or deterministic code when the shape is stable
```

Projects do not need to move all the way to the right. Many useful artifacts stay part
prose, part structured data forever.

### "Hard schema, soft authoring"

The name "softschema" can mislead. It is the opposite of weak validation: the contract
is strict (Pydantic and JSON Schema, both with `extra="forbid"` semantics by default),
but the authored document remains narrative, editable, and gradually migratable. "Soft"
describes the authoring experience and the adoption path, not the boundary enforcement.

A team can ship a permissive boundary today and tighten it later. The schema can
evolve. The Markdown body stays readable through the whole journey.

### Adjacent approaches and why they don't fit

- **Plain JSON Schema in a YAML file.** Works for pure-data artifacts. Fails for
  artifacts that mix narrative prose with structured values, because nothing tells a
  consumer *which* values are authoritative and where they live.
- **Pydantic (or any source schema) alone.** Carries Python semantics that don't travel
  cross-language. Loses the portable structural subset that other implementations could
  validate.
- **Full-body form parsers** (Markform, custom Markdown body bindings). Powerful, but
  they own a Markdown body parser and a render runtime. Softschema deliberately does
  not. A body-form runtime can sit *above* softschema, export a values dict, and call
  softschema for validation — no shared code required.
- **Provider structured-output adapters.** Useful at the LLM boundary, but they
  validate one provider's subset; softschema validates the full schema after the model
  responds. The two compose; the adapter is not a substitute.
- **Plain Markdown with hand-maintained convention.** This is the starting state for
  most projects. Softschema is the smallest possible step up: add metadata, add a
  contract ID, validate the values consumers actually read.

## Design Philosophy

### Core principles

1. **The source model is the source of truth in its host language.** In Python, that
   is Pydantic. In a future TypeScript implementation, it is Zod. The source model
   carries constraints, cross-field invariants, and the field metadata that drives
   downstream tooling.
2. **The JSON Schema sidecar is the portable artifact.** It is generated from the
   source model, committed to the repository, and consumed by validators, generated
   sections, and cross-language tooling. JSON Schema is the language-neutral
   structural surface.
3. **Cross-field invariants live in the source model.** JSON Schema cannot cleanly
   express conditional invariants ("if A is set, B must satisfy P"), so they live in
   the source model (`@model_validator` in Pydantic, `.refine` in Zod). This is why
   semantic validation requires the source-model class and cannot run cross-language.
4. **One native document profile.** Frontmatter values plus narrative Markdown body.
   No body-binding tags, no body parser inside softschema.
5. **Softschema is consumer-agnostic at the values layer.** Anything that produces a
   values dict — a frontmatter parser, a body-form runtime, a structured-output
   adapter, a hand-written test fixture — can call `validate_values`. The first
   release ships only the frontmatter consumer because it covers the common case.
6. **Generated sections eliminate drift.** Any schema fact that appears in two places
   (a controlled vocabulary in a runbook, an enum list in QA code, a field map in a
   judge prompt) has one of those places become a generated section. CI fails on
   drift.
7. **`x-softschema` is annotation only.** It carries authoring metadata (group, owner,
   tier, instruction, aliases, repair) that downstream tooling consumes. It is *not* a
   second validation language. Cross-field invariants stay in the source model.
8. **The first release is small and self-contained.** Compile, validate, generate
   sections, and the resources to teach the pattern. Patches, mirrors, materialization,
   provider adapters, body-form bridges, and a language-neutral invariant DSL are all
   reserved.

### Boundary-driven hardening

Add structure because a downstream consumer needs it, not because more structure feels
better. The default validation mode for a new schema is `permissive` — known fields are
checked, unknown fields are tolerated — until repeated failures or fixture audits show
unknown fields are actually bugs. Then the schema graduates to `enforced`.

This protects projects from over-hardening too early. An agent that produces 20-field
records will inevitably emit something slightly off; if the schema is enforced from day
one, every off-field becomes a validation failure instead of an informational warning.

### What softschema is not

- It is not a Markdown body parser. Body prose is reader-facing; consumers do not parse
  body tables for structured values.
- It is not a form runtime. A body-form runtime is a different layer that can sit above
  softschema.
- It is not a repair engine. Aliases are an annotation hint; controlled-vocabulary
  repair is deferred until a concrete consumer earns the design.
- It is not a workflow orchestrator. Process graphs, plugin discovery, and structure
  reports are host-framework responsibilities.
- It is not a structured-output provider adapter. Provider-side validation is a
  separate, deferred concern.

## Artifact Layer

This section summarizes the language-neutral artifact rules. The [spec](softschema-spec.md)
is authoritative.

### Profile A: frontmatter values plus narrative body

The single native profile:

```markdown
---
softschema:
  contract: example.movies:MoviePage/v1
  status: enforced
movie:
  title: Spirited Away
  release_year: 2001
  ratings:
    rotten_tomatoes:
      critics:
        score_percent: 96
        total_reviews: 225
---
# Spirited Away (2001)

Plain Markdown body. Structured consumers must read the YAML payload, never the body.
```

Frontmatter holds the values. The body is plain Markdown — narrative, optional tables,
caveats — but it is a projection for readers, not a data source.

### The `softschema:` metadata block

| Field | Required | Meaning |
| --- | --- | --- |
| `contract` | Yes for self-describing documents | The stable contract ID. |
| `status` | No | Boundary maturity — `soft`, `permissive`, or `enforced`. |

Invalid `softschema:` metadata is a validation error. The block is required for new
templates; legacy instances may omit it and rely on host-side resolution. CLI flags
override document metadata when present.

### Contract IDs

Recommended form: `namespace:UpperCamelCaseName/version`. Examples:

- `example.movies:MoviePage/v1`
- `example.docs:IncidentReview/v1`
- `com.acme.docs:IncidentReview/1.0`

A contract ID names a payload contract, not an implementation. The same contract can
map to Pydantic in Python, Zod in TypeScript, a JSON Schema sidecar, a database record,
or a hand-authored validator. The ID does not need to resolve to a class in any
particular language.

Style notes:

- Class-like names are familiar across languages and read well in prose.
- A namespace becomes useful when the contract may travel between repositories or
  organizations.
- A version becomes useful when the contract may change independently of any
  implementation.
- Avoid implementation-noisy names like `MoviePageEnvelope` unless the envelope itself
  is the content contract.

### Status taxonomy

| Status | Meaning |
| --- | --- |
| `soft` | A convention exists, but no boundary schema is enforced. |
| `permissive` | Known fields validate; extension fields may be allowed by the source model. |
| `enforced` | The schema is authoritative at the boundary. |

Status records intended maturity; it does not change validation behavior by itself.
Whether a model allows extra fields is configured on the source model, not on the
binding. A `legacy` status existed in earlier internal designs and was rejected for
the public release — see [Rejected Alternatives](#rejected-alternatives).

### Envelope

Normal artifacts have one top-level payload key beside `softschema:`. A CLI or host can
infer the envelope when exactly one non-`softschema` top-level key exists. Multiple
payload keys require explicit disambiguation.

### Source-of-truth rules

Structured consumers should read, in order of project convention:

1. YAML frontmatter payload values.
2. Declared YAML data sidecars (when the host project defines that convention).
3. Pure data files.

Markdown body prose and tables are reader-facing. They may mirror structured values,
but they are not authoritative. Body tables exist for human scanning; tools that try to
parse them break as soon as a human edits the prose around them.

### Schema sidecars vs data sidecars

These are two different concepts that share the word "sidecar":

- **Schema sidecars** describe the validation contract — generated JSON Schema written
  as YAML. Always supported.
- **Data sidecars** hold artifact payload values outside the Markdown frontmatter.
  Useful for large or machine-generated payloads. The first release does not implement
  generic data-sidecar loading; a host project can define its own convention if
  needed.

The general rule: inline-small, sidecar-large. Use frontmatter for small consumed
payloads. Consider a data sidecar only when the structured payload is large,
machine-generated, or would distract a reader. When a host project uses data sidecars,
keep routing fields such as `softschema.contract` and a short summary in frontmatter,
and document exactly how consumers find and validate the sidecar.

## Validation Architecture

### Two independent engines

Structural and semantic validation are two engines that run independently and report
independently:

- **Structural** validation runs JSON Schema against the sidecar (using `jsonschema` in
  Python, `ajv` or equivalent in TypeScript). It is cross-language and works without
  the source-model class. It catches type mismatches, enum violations,
  missing-required fields, and shape errors.
- **Semantic** validation runs the source model (`model_validate` in Pydantic,
  `safeParse` in Zod). It runs type validation, field constraints, enum checks, *and*
  cross-field invariants. It requires the source-model class and is host-language only.

The two engines usually agree on shape but they are not identical: Pydantic validation
is not "JSON Schema validation that happens to be in Python." When both run, they run
independently and report independently. A consumer that sees `structural.ok: true`
without `semantic.ok: true` knows that cross-field invariants were not checked.

### Where invariants live

| Kind | Lives in | Example |
| --- | --- | --- |
| Single-field type, range, regex, enum | JSON Schema | `score_percent: 0..100` |
| Cross-field invariants | Source model | "If `direction=up` then `delta_pct > 0`" |
| Authoring metadata | `x-softschema` annotations | `tier: hard_fact`, `owner: agent` |

Cross-field invariants cannot be cleanly expressed in JSON Schema, which is why the
source model remains canonical and semantic validation requires the source-model class.

### Value resolution

Frontmatter is the default value carrier, but the resolver layer is explicit. Three
modes:

| Mode | Use |
| --- | --- |
| `values_key` (default for new docs) | Values live at a JSON pointer (default `/values`); frontmatter-level metadata is excluded. |
| `frontmatter_root` (compatibility seam) | Values live at the frontmatter root; metadata keys are removed via `exclude_keys`. |
| `host_adapter` | The host supplies a callable that returns the values dict. Use when neither shape applies. |

For new documents, the canonical shape uses `values_key`:

```yaml
softschema:
  contract: example.movies:MoviePage/v1
  values:
    location: frontmatter
    pointer: /values

values:
  movie:
    ...
```

The current Python release infers the envelope from the first non-`softschema`
top-level key, which is equivalent to the `frontmatter_root` mode without explicit
configuration. The explicit `softschema.values: {location, pointer}` syntax is the
forward-compatible shape that a later release will adopt.

### `softschema:` block policy by document state

| Document state | Policy |
| --- | --- |
| Existing legacy instances | Block optional. Host resolves the schema by file path or call site. |
| New templates | Block required. The template self-describes its schema. |
| New generated instances | Block required, unless the artifact is intentionally host-bound. |
| CLI invocations | `--schema` and `--model` override document metadata when present. |

This policy lets large legacy corpora stay unchanged while every new artifact is
self-describing.

### Schema/model `$id` mismatch check

When both document metadata (`softschema.contract`) and a `--model` flag are present,
softschema asserts that the model's generated `$id` matches the document contract.
Mismatch fails the run unless explicitly allowed. This is a cheap guardrail against
operator mistakes (running one contract's validator against another's document).

## Schema Bundle Format

### JSON Schema 2020-12 with `x-softschema` annotations

The compiler emits one YAML file per schema:

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id: example.movies:MoviePage/v1
title: MoviePageEnvelope

x-softschema:
  contract: example.movies:MoviePage/v1
  generated_from: example_app.schemas.movie_page:MoviePageEnvelope
  softschema_format_version: 1
  schema_sha256: a3f7...

type: object
required: [movie]
properties:
  movie:
    $ref: "#/$defs/MoviePage"

$defs:
  MoviePage:
    type: object
    additionalProperties: false
    required: [title, release_year]
    properties:
      title:
        type: string
        description: Display title.
```

Plain JSON Schema validators validate shape; the softschema runtime additionally reads
`x-softschema` for agent metadata, alias tables, and renderer hints. Validator
configuration note: some validators warn on unknown keywords in strict modes. The
Python wrapper handles this transparently; TypeScript adopters will need to register
`x-softschema` with `ajv` or set `strict: false`.

### Root annotations (shipped)

| Field | Meaning |
| --- | --- |
| `contract` | The contract ID this schema represents. |
| `generated_from` | The source-model symbol the schema was generated from. |
| `softschema_format_version` | Version of the `x-softschema` block format. |
| `schema_sha256` | Deterministic hash of the canonical-JSON form of the schema. |

### Field-level annotations (planned)

Per-field `x-softschema` blocks let a source model carry authoring metadata that
travels into the JSON Schema sidecar:

| Key | Meaning |
| --- | --- |
| `group` | Authoring group label for related fields. |
| `order` | Display order within a group. |
| `tier` | `hard_fact` / `constrained` / `narrative`. |
| `owner` | Who or what produces the value: `agent`, `postprocess`, `system`, `human`. |
| `instruction` | Short string aimed at agents filling the field. |
| `examples` | Example values for prompts and documentation. |
| `aliases` | Controlled-vocabulary repair table. See alias semantics below. |
| `repair` | `none` / `safe_coerce` / `suggest_alias`. |

A small `SField()` helper (planned) wraps Pydantic `Field()` and validates the metadata
shape at author time, so typos like `owner="agennt"` fail at type-check rather than at
compile. Once shipped, downstream tooling (QA rules, agent prompts, comparison logic,
generated documentation) reads these annotations through `SchemaView` rather than
re-introspecting the source model.

These annotations are advisory. They do not change validation; they are pure
authoring/runtime metadata.

### Alias semantics

`aliases` on a field is a controlled-vocabulary repair table — strings an agent might
plausibly emit that map to canonical enum values. The runtime treats them as follows:

- An alias with **one** target is exact and may be auto-repaired only when the field's
  `repair` is `safe_coerce`.
- An alias with **multiple** targets is ambiguous and must produce a *proposed* repair,
  not an automatic rewrite, regardless of `repair` setting.
- Alias matching is case-insensitive and whitespace-normalized unless the field opts
  out via a future `match_strict: true` attribute.
- Aliases are authoring/repair metadata only. They do **not** extend the JSON Schema
  enum; downstream validators still reject the alias string. Resolution happens in the
  softschema runtime before validation, or as part of a (future) repair pass.

This rule prevents aliases from quietly becoming a second enum language. The actual
repair workflow is deferred until a concrete consumer earns the design.

### Canonical hashing

Schema hashes are load-bearing in two places: (a) `compile --check` depends on
deterministic sidecar output, and (b) generated-section markers carry a `sha256`
attribute pinning the section to a specific schema revision. Both must compute the
same hash regardless of YAML formatting.

The hash is **SHA-256 over a canonical JSON representation**, not over the
human-formatted YAML bytes:

- UTF-8 encoding.
- JSON object keys sorted lexicographically at every nesting level.
- No insignificant whitespace.
- No `generated_at` timestamp in the hashable representation.
- `x-softschema` annotations included.
- Numbers in canonical JSON form.

The committed sidecar stays YAML for readability. The hash is computed by serializing
the parsed JSON Schema document to canonical JSON and hashing that byte stream. Two
sidecars that round-trip to the same JSON Schema produce the same hash even if their
YAML formatting differs.

This is the schema-side rule. Value canonicalization (for instance values in a
materialized sidecar) is deferred until materialization itself lands.

### Schema reference resolution

Documents reference schemas by path today. URN-based references with a repo-level
registry are reserved:

```yaml
# By path (relative to the document)
softschema:
  schema:
    ref: ../../schemas/movie-page.v1.schema.yaml

# By URN (planned; resolved through a repo registry)
softschema:
  schema:
    ref: urn:example.docs:MoviePage:v1
```

When URN resolution ships, a small repo-level `softschema.yaml` registry maps URNs to
file paths so every consumer resolves them the same way. Mismatches between a path-loaded
schema's `$id` and a supplied URN will be a hard error.

### CI drift detection

```bash
softschema compile <module:Class> --check schemas/<name>.schema.yaml
```

The committed sidecar is *generated, but committed*. The CI check fails if the
committed schema drifts from the source model. Fix: re-run without `--check` and
commit the regenerated sidecar.

## Generated Sections (planned)

This is the headline follow-on feature after the v0.1 release. The goal: eliminate
schema-fact duplication across documents.

### The drift problem

Any schema fact that appears in two places will drift. A controlled vocabulary in a
runbook diverges from the enum in the source model. A field map in a judge prompt
becomes stale when a field is renamed. An enum constants table in QA code lags behind
the schema by a release. Each of these is a hand-maintained table that should be
generated.

Generated sections fix this by making the schema generative: any documented schema
fact lives in exactly one source (the schema) and gets rendered into Markdown via a
marker that CI can re-render on drift.

### Namespaced markers

```markdown
<!-- softschema:generated kind="enum_table" contract="example.movies:MoviePage/v1" sha256="..." -->
| Field | Allowed values |
| --- | --- |
| genre | drama, comedy, action, animation |
<!-- /softschema:generated -->
```

The `softschema:` namespace prevents collision with other tools' `<!-- generated -->`
markers. The closing tag matches.

### Language-aware markers

For non-Markdown targets, use language-appropriate comment syntax. HTML comments do
not belong in Python source:

| Target | Marker syntax |
| --- | --- |
| Markdown | `<!-- softschema:generated ... -->` … `<!-- /softschema:generated -->` |
| Python | `# <softschema:generated ...>` … `# </softschema:generated>` |
| YAML / TOML | `# softschema:generated ...` … `# /softschema:generated` |

For Python, prefer a fully generated standalone module over marker blocks inside
hand-authored source. A standalone module that softschema entirely owns avoids
partial-file ownership confusion.

### Section attributes

A generated section needs more than `kind`:

| Attribute | Purpose |
| --- | --- |
| `kind` | `enum_table` / `field_list` / `vocab` (Phase 0). |
| `contract` | Contract ID or schema path. |
| `root` | JSON Pointer to the entry definition (default `#`). |
| `view` | Named preset defined in the schema's root `x-softschema.views`. |
| `include_paths` / `exclude_paths` | JSON Pointer lists. |
| `include_groups` / `include_owner` / `include_tier` | Filter by `x-softschema` metadata. |
| `format` | `markdown_table` / `markdown_list` / `plain` / `yaml` / `json`. |
| `sort` | `schema_order` / `alphabetical` / `tier`. |
| `sha256` | Hash of the schema bundle that produced the section. Informational. |

Single-line markers handle simple sections; a YAML block form handles complex
attribute sets. Both forms are equally valid; the generator canonicalizes back to
whichever form was used in the source.

### Views

Most generated sections need a curated subset of fields (a judge prompt wants
different fields than a runbook's controlled-vocab table). Rather than spreading
filter attributes across every marker, define **views** in the schema's root
`x-softschema`:

```yaml
x-softschema:
  contract: example.movies:MoviePage/v1
  views:
    all_enums:
      kind: enum_table
      include_enums: true
      sort: schema_order
    judge:
      kind: field_list
      include_owner: [agent, postprocess]
      include_groups: [identity, qualitative]
      format: markdown_list
```

A marker with `view="judge"` resolves the preset and applies any additional attributes
on top.

### `SchemaView` — shared reader

QA reads enum values from the sidecar, comparison logic reads `x-softschema.tier`,
generated sections walk the schema fields. If each consumer parses JSON Schema
independently, the drift problem is recreated *inside the readers*. The package ships
a small shared schema reader so every consumer goes through one logic path:

```python
class SchemaView:
    """Read-only view over a compiled schema bundle."""

    @classmethod
    def load(cls, schema_path: Path) -> "SchemaView": ...

    @property
    def contract_id(self) -> str: ...
    @property
    def schema_sha256(self) -> str: ...

    def iter_fields(self) -> Iterable[FieldInfo]: ...
    def field(self, pointer: str) -> FieldInfo: ...
    def enum_values(self, pointer: str) -> list[str] | None: ...
    def fields_by_group(self, group: str) -> list[FieldInfo]: ...
    def fields_by_owner(self, owner: str) -> list[FieldInfo]: ...
    def fields_by_tier(self, tier: str) -> list[FieldInfo]: ...
    def view(self, name: str) -> "FieldQuery": ...
```

`SchemaView` is what makes "downstream consumers read the schema bundle directly"
safe. Generated sections, QA enum lookups, and comparison tier maps all consume the
same `FieldInfo` shape.

### Hash semantics

The `sha256` attribute on a generated-section marker records the schema-bundle hash
used to render the section. It is checked by `generate --check` and indicates whether
the rendered content is in sync with the current schema. It is *not* used to reject
the containing document during normal validation. A document with a stale generated
section is a CI build issue (regenerate and commit), not a document-validity issue.

### Generated sections versus mirrors

These are different mechanisms that share a marker syntax:

- **Generated sections** render *schema facts* — enum values, field names, types,
  vocabularies.
- **Mirrors** render *instance values* — values from the document's own frontmatter
  reflected back into the body for readers.

The first release ships generated sections only. Mirrors are reserved. When mirrors
arrive, the marker namespace will distinguish them:

```text
<!-- softschema:generated kind="schema.enum_table" ... -->     # schema-derived
<!-- softschema:generated kind="value.price_table" ... -->     # instance-derived (future)
```

### CI integration

```bash
softschema generate [paths...]            # regenerate in place
softschema generate --check [paths...]    # fail nonzero on drift
```

CI runs `--check`. Adding a new enum value to the source model and forgetting to
regenerate fails the build; rerunning `softschema generate` and committing the result
fixes it.

## Runtime API Surface

### Minimal Phase 0 surface

```python
def compile(model_cls, out_path) -> CompileResult:
    """Emit the JSON Schema sidecar from a source-model class."""

def validate_values(
    values: dict,
    *,
    model: type[BaseModel] | None = None,
    schema: Path | None = None,
) -> ValidationReport:
    """Run structural and/or semantic validation; never raises for validation failures.

    Returns a ValidationReport with separate `structural` and `semantic` results.
    Either, both, or neither engine may run depending on which of `model`/`schema`
    is passed; engines that did not run are reported as `skipped` with a `reason`.
    """

def model_validate_strict(values: dict, model: type[BaseModel]) -> BaseModel:
    """Thin convenience wrapper over `model.model_validate(values)`. Raises on failure.

    Use when host code wants source-model-native exception-raising behavior. The CLI
    and `validate_values` use the non-raising report path.
    """

def generate_sections(paths: list[Path], *, check: bool = False) -> GenerateResult:
    """Regenerate <!-- softschema:generated --> blocks. With check=True, fail on drift."""
```

The non-raising `validate_values` path is the primary API. The raising
`model_validate_strict` is a convenience wrapper for callers that want the source
model's native exception type.

### CLI commands

Today's CLI surface:

```bash
# Validate
softschema validate <doc.md> --schema <schema.yaml>                   # structural only
softschema validate <doc.md> --model <module:Class>                   # semantic only
softschema validate <doc.md> --schema <schema.yaml> --model <module:Class>  # both

# Compile
softschema compile <module:Class> --out <schema.yaml>
softschema compile <module:Class> --check <schema.yaml>

# Inspect / discover
softschema inspect <doc.md>
softschema docs [topic] [--list] [--json]
softschema skill [--brief]
```

Planned (lands with generated sections and `SchemaView`):

```bash
softschema validate-values <values.yaml> --model <module:Class>
softschema validate-values <values.yaml> --pointer /values --model <module:Class>

softschema generate [paths...]
softschema generate --check [paths...]

softschema schema-info <schema.yaml> --enum-table
softschema schema-info <schema.yaml> --view judge
```

`validate-values` expects the values object at the YAML root by default. Use
`--pointer /values` for wrapped files (such as a materialized sidecar with a
`softschema/values` envelope).

`--allow-schema-mismatch` is available on `validate` to opt out of the schema/model
`$id` check; default is to error on mismatch.

## YAML Subset

A conservative YAML subset is enforced for authored frontmatter values. The subset is
intentionally narrow so that artifacts are unambiguous to read, easy to canonicalize,
and safe across YAML 1.1/1.2 parser quirks.

### Allowed

- Mappings with string keys.
- Sequences.
- Strings (single-line, double-quoted, single-quoted, plain, or block scalars).
- Numbers (integer, float).
- Booleans `true` / `false`.
- Null (`null`, `~`, or empty).
- ISO 8601 date and date-time strings (parsed as strings, normalized at the schema
  layer).
- Block scalars (`|`, `>`).

### Forbidden

- Anchors (`&foo`) and aliases (`*foo`).
- Custom tags (`!foo`).
- Duplicate keys in a mapping.
- Implicit YAML 1.1 booleans (`yes`/`no`/`on`/`off`/`y`/`n`).
- Non-string mapping keys.

The subset is enforced by tests, not just prose. Comment preservation is **not** a
first-release requirement; it lands with patches or in-place normalization (deferred).
Value canonicalization (sorted keys, deterministic float formatting for instance
values) is also deferred — it becomes load-bearing only when a materialized canonical
sidecar exists.

## Python Implementation

The Python package is the first concrete implementation. It ships at the root of this
repository and is built from `packages/python/src/softschema`.

### Package layout

```text
packages/python/src/softschema/
  __init__.py           # public API re-exports
  cli.py                # CLI entry point (validate, compile, inspect, docs, skill)
  compile.py            # Pydantic → JSON Schema YAML sidecar; canonical-JSON hashing
  models.py             # SoftschemaBinding, SoftschemaMetadata, SoftschemaStatus, SoftschemaProfile,
                        # SoftschemaStage, SoftschemaWarning, ValidationResult
  registry.py           # SoftschemaRegistry (complete-binding registration)
  validate.py           # validate_artifact, validate_values, ValueResolver
  py.typed              # PEP 561 marker
```

### Public API

```python
from softschema import (
    SoftschemaBinding,
    SoftschemaRegistry,
    SoftschemaStatus,
    SoftschemaMetadata,
    SoftschemaWarning,
    compile_model,
    validate_artifact,
)
```

### Binding fields

```python
SoftschemaBinding(
    contract_id="example.movies:MoviePage/v1",
    model=MoviePage,                  # optional Pydantic model
    envelope_key="movie",             # expected top-level payload key
    status=SoftschemaStatus.enforced,           # soft / permissive / enforced
    profile=SoftschemaProfile.frontmatter_md,  # frontmatter-md / pure-yaml
    schema_path=Path("..."),          # optional JSON Schema YAML sidecar
    owner="example_app",              # optional, informational
)
```

The registry registers complete bindings. It does not expose aliases, compatibility
maps, or incremental registration helpers — alias resolution is a host concern when it
is needed.

### CLI resolution

The CLI reads `softschema.contract`, `softschema.status`, and a single top-level
envelope key from the artifact by default. `--contract`, `--status`, and `--envelope`
are override and disambiguation flags.

`softschema validate` requires a validation implementation (`--model`, `--schema`, or
both), because document metadata identifies the contract but does not import code.

### Bundled resources

The Python wheel bundles the guide, spec, this design doc, the skill, and the
movie-page example. The `softschema docs` and `softschema skill` commands print those
bundled resources from `softschema/resources/` so agents in installed environments can
discover the material without knowing the source-checkout layout.
`softschema docs --list --json` exposes the topic directory as structured data for
automation.

### Dependency boundary

The package depends only on:

- `frontmatter-format` for Markdown frontmatter and YAML reading.
- `jsonschema` for structural validation.
- `pydantic` for semantic validation and source-model definition.
- `pyyaml` for YAML serialization.

It must not import host frameworks, domain packages, browser packages, GCP libraries,
or process-orchestration code. `frontmatter-format` is the frontmatter/YAML mechanics
dependency; it is not a generic softschema data-sidecar runtime.

### Validation failure modes

Validation fails on:

- malformed frontmatter
- invalid `softschema:` metadata
- missing envelopes when the contract requires one
- missing or unreadable schema sidecars when a binding declares one
- JSON Schema errors (structural)
- Pydantic errors (semantic)

Structural and semantic errors are reported on separate fields of the result. A
caller can distinguish "shape was wrong" from "cross-field invariant failed" without
parsing error messages.

## TypeScript Implementation

This section is a placeholder for the future TypeScript implementation. The first
release ships only the Python package; `packages/typescript/` contains a README stub
that records the intent and constraints, not unused code.

### Planned shape

A future TypeScript package will be an idiomatic Zod-first port, not a Python
translation:

- **Source schemas in Zod.** Zod is the host-language source of truth for TypeScript
  consumers, the analogue of Pydantic for Python consumers.
- **`safeParse` for runtime validation.** Non-raising, returns a discriminated-union
  result. Matches the non-raising `validate_values` shape of the Python API.
- **JSON Schema export as the structural sidecar.** Generated from Zod for portability.
  Same canonical-JSON hashing rule as the Python compiler.
- **`yaml` for YAML parsing.** Same artifact format, same conservative subset.
- **Result shapes equivalent to the Python results.** Separate `structural` and
  `semantic` fields; same `status` taxonomy; same `x-softschema` annotation
  vocabulary.

### Cross-language consistency

JSON Schema plus `x-softschema` is the portability boundary. Both packages emit and
consume the same bundle shape, the same artifact format, the same contract IDs, the
same metadata vocabulary. Implementation-specific invariants stay in the source model
(Pydantic for Python, Zod refinements for TypeScript) and do not need to round-trip
across languages.

### Out of scope today

No TypeScript runtime, build, or package is shipped in the first release. The Zod
implementation will be designed and built once a concrete TypeScript consumer exists.
Until then, the language-neutral docs deliberately avoid Python-specific phrasing
("source model" instead of "Pydantic model" outside the Python implementation section)
so that the cross-language contract stays clean.

## Capability Roadmap

### Shipped (v0.1)

- Artifact validation (structural and semantic, reported separately).
- Pydantic-to-JSON-Schema compilation with deterministic output and `--check` for
  drift detection.
- Root-level `x-softschema` annotations (`contract`, `generated_from`,
  `softschema_format_version`, `schema_sha256`).
- CLI: `validate`, `compile`, `inspect`, `docs`, `skill`.
- Bundled docs and example resources in the wheel.
- Public movie-page example with host-integration code.

### P0 — needed before non-trivial external consumers depend on the package

These items make the package useful for downstream tooling beyond the example.

- **Field-level `x-softschema` annotations.** `SField()` helper and compiler support
  for per-property `x-softschema` blocks carrying `tier`, `owner`, `group`,
  `instruction`, `aliases`, `repair`, and `examples`.
- **`SchemaView` reader.** Small, generic JSON Schema navigator that exposes enums,
  required fields, field metadata, and `x-softschema` annotations through one stable
  API. Eliminates the drift surface inside ad-hoc readers.
- **Stable warning-code prefix scheme.** Enumerate and document every warning code
  emitted by the package. Commit publicly to the `document-*` prefix family so
  downstream filters survive.

### P1 — make the package immediately useful for adoption-stage projects

- **Generated schema sections.** Marker format, renderer, CLI `generate` and
  `generate --check`. Depends on `SchemaView`. Eliminates hand-maintained enum tables
  and field maps that drift from the schema.
- **Lifecycle walkthrough.** A guide section with concrete recipes for each step of
  the promotion path (prose → conventions → frontmatter → validated → pure data).
- **Sidecar doctrine.** "Inline-small, sidecar-large" rule in the guide with one
  example each side.
- **Migration recipe.** Document `ValueResolver` modes as a bridge from legacy
  envelopes to the canonical shape, with a before/after artifact pair.
- **CI integration recipe.** `softschema compile --check` and `softschema generate
  --check` in a one-screen GitHub Actions snippet plus a `pre-commit` example.

### Deferred (P2)

Each of these is named and scoped here so the public surface stays small while the
direction is recorded. Each is "earned by" a concrete consumer; none ship until one
arrives.

- **Alias-repair semantics.** Controlled-vocabulary single-target / multi-target
  resolution from the alias annotation. Useful for agent-generated artifacts with
  typo tolerance. Risk: aliases can grow into a second enum language if not scoped
  carefully.
- **URN-based schema references.** Repo-level `softschema.yaml` registry mapping URNs
  to file paths. Useful for cross-repo schema sharing; most projects can stay
  path-only.
- **Patch protocol and fill loop.** `set`/`replace`/`append`/`insert`/`remove`/`test`
  operations addressed by JSON Pointer, plus an `inspect` API for agent-driven
  incremental fill. Earned by an artifact whose authoring is naturally multi-pass.
- **Mirrors / value-derived sections.** Instance values rendered back into the body
  via the same marker namespace. Earned by an artifact (such as a probability table
  inside a prediction record) that benefits from inline value display kept in sync
  with frontmatter.
- **Materialization sidecar.** `<doc>.values.yaml` with `source.sha256` integrity
  check. A verified cache, not a second source of truth. Earned by a downstream
  consumer that benefits from a hash-linked canonical cache.
- **YAML canonicalization for values.** Lands with materialization; without a
  hash-linked sidecar, there is nothing to canonicalize for.
- **Provider structured-output adapters.** `export_provider_schema(bundle,
  provider="anthropic" | "openai" | "vertex")` to down-convert the schema for
  provider-side validation. Earned by a production path through one of those provider
  schemas where structural enforcement at the model boundary is worth the
  maintenance cost.
- **Schema versioning migration tooling.** `softschema migrate ... --from ... --to ...
  --map ...`. Earned by the first v2 → v3 migration.
- **Language-neutral invariant DSL.** Beyond the small `aggregate` ops (sum, count,
  all-equal, exists). Earned by a cross-language consumer that needs more than
  `aggregate` covers.
- **Body-form runtime integration.** When a body-form runtime arrives, the bridge is
  one call: the runtime parses the body, exports a values dict, and calls
  `validate_values`. No softschema-side feature work; no shared code. The runtime
  optionally consumes the softschema bundle convention; softschema remains usable
  without it.

## Accepted

Decisions that have been made and are not under revisitation in the near term:

- The mental model and artifact format are programming-language agnostic.
- `softschema.contract` is the public metadata key for the contract ID.
- Contract IDs use `namespace:UpperCamelCaseName/version`.
- The first Python package lives at the repo root for uv and PyPI simplicity, with
  source under `packages/python`.
- TypeScript/Zod is a reserved future path, represented today only by a README stub.
- Invalid `softschema:` metadata is a validation error, not a warning.
- The public repo does not carry private compatibility shims.
- The Python wheel bundles guide, spec, design doc, skill, and example resources.
- Examples are copyable source files. The CLI may print them but does not scaffold or
  mutate other projects.
- Structural and semantic validation are independent engines, reported separately.
- `x-softschema` is annotation-only and never a second validation language.
- Cross-field invariants live in the source model.
- The Python package does not model process graphs, emit structure reports, or do
  plugin discovery. Those are host-framework responsibilities.

## Deferred

Items the design accommodates but the first release does not implement. See the
[Capability Roadmap](#capability-roadmap) above for the prioritized list.

## Rejected Alternatives

Decisions made by *not* choosing an option that was explicitly considered:

- **Preserving a `legacy` status.** Earlier internal designs had `soft / permissive /
  enforced / legacy`. `legacy` carries no boundary semantics and exists only as an
  adoption-history marker. The public package commits to one of three meaningful
  values and forces a real choice at adoption time.
- **Preserving alias resolution as public API.** Earlier internal designs let bindings
  declare alias schema IDs that resolved to a canonical ID. The public registry
  registers complete bindings only. Alias-style indirection, when needed, is a host
  concern; the host can layer its own resolver on top of `SoftschemaRegistry`.
- **Making source-language class names the required public contract IDs.** Earlier
  internal practice used `<module>:<ClassName>/<version>` tokens. That worked for a
  private Python-first migration, but it bakes a Python binding into the public
  format. The contract ID is an artifact-content name. It may resemble a class name
  but is not required to resolve to one.
- **Parsing Markdown body tables as the source of structured values.** Tables in the
  body exist for human scanning. Tools that parse them break the moment a human edits
  the prose around them. The YAML payload is authoritative; tables can mirror values
  for readers.
- **Bundling a body-form parser into softschema core.** A body-form runtime is a
  different layer that can sit above softschema. Including it would mean owning a
  Markdown body parser and a render runtime, and would couple softschema to one
  specific body-form convention. Softschema is consumer-agnostic at the values layer;
  any runtime that produces a values dict can call it.

## References

- [Softschema Guide](softschema-guide.md) — teaching reference for humans and agents.
- [Softschema Spec](softschema-spec.md) — exact artifact format rules.
- [README](../README.md) — short orientation and quick commands.
- [Movie Page Example](../examples/movie_page/README.md) — the working public example.
- [Public Readiness Plan](project/specs/active/plan-2026-05-24-softschema-public-readiness.md)
  — time-bounded execution roadmap; the source of P0/P1/Deferred capability lists.
- [Runtime Design v8](research/research-2026-05-24-softschema-runtime-design-v8.md) —
  earlier exploratory research; the substance has been folded into this document, and
  this document supersedes it. Retained for context until it is retired.

<!-- This document follows std-doc-guidelines.md. Review guidelines before editing. -->
