# softschema Guide

`softschema` applies gradual contracts to YAML data.
The standard profile is Markdown with YAML frontmatter and an optional body.
Pure YAML is also supported when the structured record stands on its own.
Start with a named convention, validate the fields that have stabilized, and make the
compiled schema authoritative once undeclared fields should fail.
This guide is the operational reference for humans and coding agents using that
progression.

For the exact file format and validation rules, see
[softschema Spec](softschema-spec.md).
Two interchangeable implementations share one portable contract: see
[Python Package Design](softschema-python-design.md) and
[TypeScript Package Design](softschema-typescript-design.md).

## Quick Start for Agents

To set up softschema in a repository with an agent, tell the agent:

> Run `uvx softschema@latest --help` (for the Python implementation) or
> `npx -y softschema@latest --help` (for the Node implementation) and follow the
> instructions to set up softschema for this repo as a skill.

The help output points the agent to the repo-local skill install command and the bundled
docs it should read next.
The skill teaches the model behind the commands: YAML is authoritative for consumed
values, the artifact profile is independent of contract maturity, and Markdown is an
optional place for reader-facing context.
The standard examples use frontmatter Markdown; pure YAML follows the same contracts and
status progression.

## What softschema Is

A **soft schema** is a data contract whose coverage and boundary strictness grow as the
records and their consumers become better understood.
A declared field can have a precise type or constraint from the start.
The “soft” part is that the contract can describe only the stable part of a record,
allow extensions while the rest is being discovered, and become authoritative later.

softschema separates two decisions:

| Decision | Choices | Meaning |
| --- | --- | --- |
| Artifact profile | `frontmatter-md`, `pure-yaml` | Add a Markdown body beside the YAML payload, or use structured data alone. |
| Contract status | `soft`, `permissive`, `enforced` | Record a convention, validate known structure under authored rules, or make a bound structural schema authoritative. |

The status progression is:

- **`soft`:** a contract convention exists, but no boundary schema is enforced.
- **`permissive`:** known fields validate; the bound model or authored schema determines
  whether extension fields are allowed.
- **`enforced`:** a bound structural schema is authoritative, and softschema applies
  checked undeclared-property rejection where the support matrix permits it.

The status records intended maturity; it does not bind a validator by itself.
A bound model or schema supplies the rules.
`soft` and `permissive` apply those authored rules as-is; `enforced` adds checked object
closure when a structural schema is bound.

The schema itself can evolve throughout this progression.
A project may add optional fields, types, enums, nested records, and cross-field
constraints while it observes a record corpus and implements consumers.
None of those changes requires a Markdown body to change.
The body may remain stable or be absent because the artifact is pure YAML.

Structure makes values reliable for code and lets validation catch errors at a boundary,
but a schema written before the data is understood can encode guesses as requirements.
Gradual contracts let agents and software formalize the stable core first, keep
extensions visible, and tighten the boundary when those extensions should become errors.

The Markdown profile complements that schema progression.
It keeps provenance, judgment, rationale, and caveats beside the payload when those do
not fit fixed fields.
The `pure-yaml` profile is a first-class option when the whole artifact is structured.

**Soft schemas** name the general practice, which can apply to database records, JSON
Schema, or other validators.
**softschema** is this repository’s YAML-based artifact format and its two behaviorally
aligned implementations: Python/Pydantic and TypeScript/Zod.
Artifact payloads use YAML in both profiles; softschema does not define a JSON artifact
profile.

## When to Use It

Use softschema when a downstream consumer needs reliable YAML values and the final
record shape is still being discovered.
Typical signals include:

- a collection of heterogeneous records needs normalization or enrichment over time;
- agents are developing producers, consumers, and the contract together;
- several software components need a shared boundary while extension fields remain
  useful;
- a later database, API, or interchange format has a stricter schema than the current
  records; or
- a record needs both structured values and prose context.

Skip softschema when:

- no downstream consumer reads structured values;
- the complete closed schema is already known and an existing validator covers every
  boundary; or
- the workflow has no YAML artifact stage and does not benefit from one for interchange
  or validation.

A typical maturity path is:

```text
loose YAML records or prose documents
  → a named contract convention                         (soft)
  → validation for the stable fields                    (permissive)
  → schema and record refinement as consumers develop  (permissive)
  → an authoritative structural boundary                (enforced)
  → validated import into a database, API, or other strict system
```

The artifact may use Markdown with frontmatter or pure YAML at every contracted step.
Many useful record collections remain permissive because extensions are part of their
design.

## Common Workflow Shapes

The pattern applies wherever records cross a boundary before their final structure is
fully known:

- **Record enhancement and harmonization.** Each source produces a pure YAML record.
  As repeated fields become understood, a contract names and validates them while
  source-specific extensions remain available.
  Aggregation code reads the validated fields and can reject malformed records at the
  boundary.
- **Software coordination.** Batch jobs, services, QA checks, and report generators use
  the same contract while it develops.
  A field becomes required only when a consumer can rely on every producer supplying it.
- **Database and API staging.** A permissive YAML record can carry fields that have not
  yet been mapped. The contract converges on the target system’s required fields and
  constraints, then enforced validation runs before import.
- **Agent pipeline handoffs.** An agent can update records and the schema in the same
  workflow, using structured errors to distinguish bad data from a constraint that was
  introduced too early.
- **Research and evaluation loops.** Measurements, confidence intervals, and verdicts
  belong in the YAML payload.
  The Markdown profile adds hypotheses, method notes, and interpretation when those need
  to travel with the record.
- **Document-backed application data.** Fields used by a UI, search index, or build step
  live in the YAML payload.
  The Markdown body holds background and long-form content when the application needs
  it.

The design test is concrete: name the consumers, the values each reads, and the point at
which an unknown field should become an error.

## Artifact Profiles

Both artifact profiles use a `softschema` metadata block.
Its self-description quartet is `contract`, `schema`, `envelope`, and `status`.

### Markdown with YAML Frontmatter

The standard examples use `frontmatter-md` because this profile demonstrates structured
data and optional context in one artifact.
Use it when the record also needs prose.
The frontmatter contains the metadata block and payload; the body remains reader-facing.
Additional frontmatter keys such as `title`, `description`, or `tags` are allowed and
ignored by softschema:

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
  mpaa_rating: PG
  directors:
    - Hayao Miyazaki
  genres:
    - Animation
    - Adventure
    - Family
  synopsis: >
    Ten-year-old Chihiro stumbles into a spirit world and must work in a magical
    bathhouse to free her parents and return home.
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
```

The `softschema:` block carries the self-description quartet: `contract` (the contract
ID), `schema` (relative path to the compiled schema), `envelope` (which top-level key
holds the payload), and `status` (validation strictness).
A fully self-describing artifact like this one validates with no flags:
`softschema validate spirited-away.md`.

The body overlaps with the YAML without mirroring it field for field: the prose adds the
film’s Oscar win, which no structured field carries, while a consumer reads only the
YAML.

The example illustrates the YAML shapes a softschema artifact can carry: constrained
integers (`release_year`, `runtime_minutes`), an enum (`mpaa_rating`), lists of strings
(`directors`, `genres`), a list of structured records (`cast`), nested objects
(`ratings.rotten_tomatoes`, `ratings.imdb`), and optional fields.

The full example, model, and generated JSON Schema live under
[examples/movie_page/](../examples/movie_page/README.md).

### Pure YAML

Use `pure-yaml` when the structured record stands on its own.
The document root after the `softschema` block is removed is the payload.
An explicit envelope is optional:

```yaml
softschema:
  contract: mycorp.runs:BacktestReport/v1
  status: soft
run_id: run-2026-04-12T18-03-00Z
summary: regression vs baseline
candidate_fields:
  cache_policy: bounded
```

This record can acquire a model and move through `permissive` to `enforced` without a
Markdown wrapper.

## Contract IDs

A contract ID names an artifact payload contract, not an implementation.
Recommended form: `namespace:UpperCamelCaseName/version`. Examples:

- `example.movies:MoviePage/v1`
- `example.docs:IncidentReview/v1`
- `com.acme.docs:IncidentReview/1.0`

The name can resemble a class or type name.
It is not required to resolve to a class in any language; the same contract may map to
Pydantic, Zod, JSON Schema, a database record, or a hand-written validator.

Picking a namespace:

- Use a short product or repository tag for internal use (`mycorp.runbooks`).
- Use reverse-DNS when the contract may travel between organizations (`com.acme.docs`).
- Use `example.*` only for documentation and demos.

Picking a version:

- Bump the version when the contract changes in a way that breaks existing consumers.
- Additive, optional fields usually don’t need a version bump.
- Keep versions short (`v1`, `v2`, `1.0`).

## Playbook: Adopt softschema for an Existing Markdown Artifact

Start with one document type, not a whole repository:

1. **Pick the artifact.** Choose one Markdown file (or family of files) that humans or
   agents already write and that a downstream consumer reads.
2. **List the consumed values.** Find every value a code path, QA check, or aggregation
   actually reads from the document.
   Anything else stays prose.
3. **Move the consumed values into YAML frontmatter** under one envelope key (for
   example, `movie:` for a movie page, `incident:` for an incident review).
4. **Add `softschema.contract`** with a stable contract ID.
5. **Pick a status.** Start with `status: soft` (no validation) or `status: permissive`
   (validate known fields under the bound model or schema’s authored extension policy).
   Save `enforced` for later.
6. **Leave the body alone.** Headings, prose, and tables for human readers stay.
7. **Validate at the boundary** (next playbook) and tighten over time.

Worked example for an incident review:

Before:

```markdown
# Incident 2026-04-12: search latency spike

Affected service: search-api
Severity: SEV-2
Duration: 38 minutes

## Summary
...
```

After (status soft; only the consumed values are in YAML):

```markdown
---
softschema:
  contract: mycorp.docs:IncidentReview/v1
  status: soft
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

The body stays unchanged.
A consumer that aggregates incidents now reads `incident.affected_service` from YAML
instead of trying to grep the body.

## Playbook: Evolve a Schema from Loose Records

This progression applies to pure YAML collections and Markdown artifacts alike.

**Step 1: collect representative records and name their consumers.** Identify which
fields current code reads, which fields recur but remain unstable, and which target
systems will eventually receive the data.
Do not infer the whole schema from one example.

**Step 2: name the convention.** Add a stable contract ID and `status: soft`. This gives
the record family an identity without requiring a boundary schema.

**Step 3: model the stable core.** Define the fields whose names, types, and meanings
are understood in Pydantic, Zod, or compiled JSON Schema.
Set `status: permissive` and validate at file boundaries.
The bound model or authored schema determines whether extension fields remain open.

**Step 4: refine the schema and the records together.** Use the corpus, validation
results, and new consumer requirements to add optional fields and constraints.
Normalize existing records before making a field required.
Keep an extension outside the contract while its meaning or type still varies.

**Step 5: enforce the structural boundary.** When unknown fields indicate authoring or
integration errors, bind a compiled structural schema and set `status: enforced`. The
validator rejects undeclared fields at the structural boundary.
If a trusted host binds only a Pydantic or Zod model, validation delegates to that
model’s language-specific rules and skips the structural layer.
This preserves native validators and refinements, but it is not portable object closure:
Pydantic and Zod have different unknown-key defaults.
Bind a compiled schema when clients in either language need the same structural result.
Setting the source model to `extra="forbid"` additionally compiles strictness into the
schema and enforces it at the semantic layer.

*Advanced, and only for composed or dependent schemas.* If every object in your schema
declares its fields in one place, the paragraph above is the complete rule and you can
skip the rest of this step.
The mechanics start to matter in two cases: declarations for one object spread across
`allOf`, `anyOf`, `oneOf`, or `$ref`, or one field’s schema depending on another field’s
value through `if`/`then`/`else` or `dependentSchemas`. There, **closing an object**
means rejecting each present property whose value is not evaluated by any successful
applicable schema at that object location, which is not what `additionalProperties`
does, because that keyword sees only the declarations sitting in its own schema object.
So a supported site receives `unevaluatedProperties: false` when declarations compose
and `additionalProperties: false` otherwise.
Structured `items` and disjoint `prefixItems`/`items` schemas close their object
elements; a `contains` schema remains a matcher so enforcement cannot change which
elements match. An explicit value for either keyword on the site still wins.
For a schema shape outside the support matrix, `status: enforced` returns
`enforcement_unsupported` instead of guessing where to insert the rule; see the
[normative support matrix](softschema-spec.md#support-matrix), and
[Playbook: Express Cross-Field Rules](#playbook-express-cross-field-rules) for a worked
dependent-field example.

**Step 6: align with a downstream hard boundary.** If the records will enter a database,
API, or other fixed system, make its required fields and constraints part of the
contract. Validate under `enforced` before the handoff.
Version the contract when a breaking change requires old and new consumers to coexist.

Artifact profile is a separate choice.
Use `pure-yaml` when the whole artifact is a structured record.
Use `frontmatter-md` when provenance, interpretation, or other prose should travel with
it. The schema and status can change without changing the Markdown body.

## Playbook: Inline Frontmatter vs. Companion Data

This playbook applies when a Markdown artifact’s structured payload grows large.
The rule of thumb is **inline-small, companion-large**:

- **Inline (frontmatter)** when the structured payload is a few dozen fields or a
  handful of small nested objects.
  Authors can see everything in one file; review comments land on the right line;
  readers don’t context-switch.
- **Companion data** when the payload is large, machine-generated, or distracting to a
  human reader. A reader who opens the Markdown file expects to read prose, not 200 lines
  of YAML.

Inline is right when the payload is compact:

```yaml
incident:
  id: 2026-04-12-search-latency
  affected_service: search-api
  severity: SEV-2
  duration_minutes: 38
```

A companion data file is right for a large machine-generated payload, such as a backtest
result:

```yaml
softschema:
  contract: mycorp.runs:BacktestReport/v1
backtest:
  run_id: 2026-04-12T18-03-00Z
  summary: "regression vs baseline"
  data:
    path: backtest-2026-04-12.values.yaml
    sha256: abc123...
```

The Markdown file keeps the routing fields (`softschema.contract`, an id, a short
summary). The full payload lives in the companion data file.

If the payload does not need the Markdown record, make it a standalone `pure-yaml`
softschema artifact and validate it directly.
softschema does not resolve an arbitrary companion path declared by another artifact.
A host project can define that relationship, resolve the path, and call
`validate_artifact()` or `validate_values()` on the result.

## Playbook: Add Python Validation

Wire a Pydantic model to a contract and validate at file boundaries:

1. **Define the model.** One Pydantic class per payload, with `extra="forbid"` on nested
   classes when the structure is settled.

   ```python
   from pydantic import BaseModel, ConfigDict, Field

   class IncidentReview(BaseModel):
       model_config = ConfigDict(extra="forbid")
       id: str
       affected_service: str
       severity: Literal["SEV-1", "SEV-2", "SEV-3"]
       duration_minutes: int = Field(ge=0)
   ```

2. **Compile a JSON Schema** so non-Python consumers can validate too:

   ```bash
   softschema compile mycorp_docs.incident:IncidentReview \
     --contract mycorp.docs:IncidentReview/v1 \
     --out schemas/incident-review.v1.schema.yaml
   ```

   **Trust note:** `--model` imports and executes local Python code.
   Use it only with trusted models.
   For untrusted input, use `--schema` with a compiled JSON Schema instead.

3. **Bind artifacts to their schema.** Add `schema:` (and `envelope:` when needed) to
   each artifact’s `softschema:` block so `softschema validate <doc>` works with no
   flags:

   ```yaml
   softschema:
     contract: mycorp.docs:IncidentReview/v1
     schema: schemas/incident-review.v1.schema.yaml
     envelope: incident
     status: permissive
   ```

   The path is relative to the document’s directory.

4. **Register a `Contract`** in your host startup (the library/host path, which outranks
   the document’s binding):

   ```python
   from softschema import Contract, Contracts, SchemaStatus

   def build_registry() -> Contracts:
       registry = Contracts()
       registry.register(
           Contract(
               id="mycorp.docs:IncidentReview/v1",
               model=IncidentReview,
               envelope_key="incident",
               status=SchemaStatus.permissive,
               schema_path=Path("schemas/incident-review.v1.schema.yaml"),
           )
       )
       return registry
   ```

5. **Validate at the boundary** (anywhere your host opens a file from disk, a queue, or
   an upload):

   ```python
   from softschema import validate_artifact
   result = validate_artifact(path, contract_id=..., registry=build_registry())
   if not result.ok:
       handle_validation_failure(result)
   ```

6. **Tighten over time.** Start `permissive`; flip to `enforced` once authoring is
   consistently clean (undeclared fields then fail structural validation), and add
   `extra="forbid"` to also enforce at the semantic layer.

The `result` object reports `structural` (JSON Schema) and `semantic` (Pydantic) errors
separately, so callers can distinguish “shape was wrong” from “cross-field invariant
failed” without parsing error strings.

## Playbook: Annotate Fields with SoftField

`SoftField` is an optional wrapper over Pydantic’s `Field` that records per-field
authoring metadata (`group`, `owner`, `tier`, `instruction`, `examples`, `aliases`,
`repair`). The compiler propagates the metadata verbatim into the compiled schema as a
per-property `x-softschema:` block.
The runtime never reads it for validation.

`SoftField` follows the same gradual-adoption rule as the rest of softschema: opt in per
field, only when a specific downstream consumer reads a specific metadata key.
The default is plain `Field`. A model whose only consumer is `validate_artifact()` does
not earn `SoftField`; the metadata would land in the compiled schema with no reader.

Consumers that earn an `SoftField` annotation:

- **Template generator.** Emits section headers from `group` and inline format hints
  from `instruction` and `examples`. Useful when authors fill a Markdown or YAML
  template by hand and the template currently carries those hints in comments that drift
  from the model.
- **Agent prompt builder.** Filters by `owner` so the agent only sees fields it owns,
  with `instruction` text rendered as guidance.
  Postprocess- and system-filled fields stay out of the prompt entirely.
- **Tier-aware QA.** Routes checks by `tier`: strict equality on `hard_fact`, enum or
  range on `constrained`, LLM-judged review on `narrative`. Lets a single QA harness
  scale without one rule per field.
- **Generated runbook sections.** `softschema generate` reads `group` for `enum_table`
  and `field_list`, and a specific pointer for `kind="vocab"`.

The light-touch end of the spectrum is plain `Field` everywhere, with no `SoftField` at
all. The structured end is `SoftField` on every field, justified by several wired
readers. Most projects sit in the middle, with a handful of `SoftField` annotations on
the fields that one or two consumers care about and plain `Field` everywhere else.
The movie example sits near the light-touch end, annotating only `genres` for the
controlled-vocabulary case.

The recognized keys and the full call shape are documented in
[Python Package Design](softschema-python-design.md).

## Playbook: Keep Schema Tables in Sync with Generated Sections

When a controlled vocabulary or field list appears in two places (a schema and a runbook
table), it will drift.
Generated sections solve this by making the runbook table a deterministic projection of
the schema.

Wrap any Markdown block you want regenerated:

```markdown
<!-- softschema:generated kind="enum_table" schema="schemas/incident.schema.yaml" -->

| Field | Allowed values |
| --- | --- |
| `severity` | SEV-1, SEV-2, SEV-3 |

<!-- /softschema:generated -->
```

Then re-render in place:

```bash
softschema generate path/to/runbook.md
```

CI runs the same command with `--check`, which exits non-zero if any block has drifted
from the current schema:

```bash
softschema generate path/to/runbook.md --check
```

Available `kind` values:

- `enum_table`: one row per enum field in the schema (`Field`, `Allowed values`).
- `field_list`: one bullet per top-level field (name, type, required, description).
- `vocab`: enum values for one specific field; requires a `pointer="/properties/foo"`
  attribute.

A worked example lives in
[examples/movie_page/README.md](../examples/movie_page/README.md); the “Schema Enums”
section is regenerated from the movie schema.

## Playbook: Validate in CI

Pin softschema as a dev dependency so CI uses a known version:

```bash
# Python
uv add --dev softschema

# Node
npm i -D softschema@latest
```

Two checks belong in CI:

- **Compiled schema drift check.** Fail the build when a committed compiled schema is
  out of sync with the source model.

  ```bash
  softschema compile mycorp_docs.incident:IncidentReview \
    --contract mycorp.docs:IncidentReview/v1 \
    --out schemas/incident-review.v1.schema.yaml --check
  ```

  **Trust note:** `--model` imports and executes local Python code.
  Use it only with trusted models.
  For untrusted input, use `--schema` with a compiled JSON Schema instead.

- **Artifact validation.** When artifacts carry the full self-description quartet
  (`contract`, `schema`, `envelope`, `status`), validation needs no per-file flags.
  This example validates both supported profiles in an artifact directory:

  ```bash
  find artifacts -type f \( -name '*.md' -o -name '*.yaml' -o -name '*.yml' \) \
    -exec softschema validate {} \;
  ```

  Override flags (`--schema`, `--envelope`, `--model`) are still available when an
  artifact does not self-describe or the host needs to override a binding.

For a full GitHub Actions snippet and a `pre-commit` hook example, see the “Continuous
integration” section of [docs/development.md](development.md).

## Playbook: Migrate an Existing Artifact

Take an artifact that does not fit either supported profile and bring it in line.

For `frontmatter-md`:

- A `softschema:` block (the self-description quartet: `contract`, `schema`, `envelope`,
  `status`) plus a designated envelope key at the top level.
- All consumed values live under the envelope key.
- Body prose is reader-facing only.

For `pure-yaml`:

- The `softschema:` block sits at the document root.
- Without an explicit envelope, the rest of the root is the payload.
- With an explicit envelope, the named key holds the payload.

Additional top-level keys (such as `title:`, `description:`, `tags:`, `pinned:`, or
other host-specific frontmatter conventions) are allowed and are not interpreted by
softschema.
Only the `softschema` block and the envelope key are softschema’s concern, so
an artifact can mix softschema with whatever metadata a static-site generator, indexer,
or other tool already expects.

Common `frontmatter-md` migrations:

**Payload values scattered at the root → values under an envelope.**

Before (payload fields directly at the root, no `softschema:` block, no envelope):

```yaml
---
title: Spirited Away
release_year: 2001
ratings:
  ...
---
```

After (a `softschema:` block plus an envelope key wrap the payload; unrelated keys could
still sit alongside):

```yaml
---
softschema:
  contract: example.movies:MoviePage/v1
  status: permissive
movie:
  title: Spirited Away
  release_year: 2001
  ratings:
    ...
---
```

**Values mixed with metadata at the frontmatter root → values under an envelope.**

Before:

```yaml
---
contract: example.movies:MoviePage/v1
status: enforced
title: Spirited Away
release_year: 2001
---
```

After:

```yaml
---
softschema:
  contract: example.movies:MoviePage/v1
  status: enforced
movie:
  title: Spirited Away
  release_year: 2001
---
```

**Body table treated as data → values in YAML, table becomes a projection.**

Before (a consumer was grepping the Markdown table):

```markdown
| Field | Value |
| --- | --- |
| Title | Spirited Away |
| Release year | 2001 |
```

After:

```markdown
---
softschema:
  contract: example.movies:MoviePage/v1
movie:
  title: Spirited Away
  release_year: 2001
---
# Spirited Away (2001)

| Field | Value |
| --- | --- |
| Title | Spirited Away |
| Release year | 2001 |
```

The table stays for readers but is no longer the source of truth.
The consumer reads YAML now.

### Dates and Timestamps Are Strings

Date- and timestamp-shaped YAML values remain portable strings, whether they are quoted
or unquoted:

```yaml
run:
  started_on: 2026-07-11
  reviewed_on: "2026-07-12"
```

Both values above decode as strings.
Existing quoted values need no edit, and artifacts that use bare date-shaped values do
not need a normalization pass.
After upgrading softschema, refresh any installed skill mirrors and validate the
artifact corpus before making optional style-only changes.

This value rule is deliberately stricter than the general-purpose reader in
`frontmatter-format`, which accepts YAML timestamps and may materialize them as Python
`date` or `datetime` values.
softschema owns artifact extraction and portable YAML parsing; the Python package uses
`frontmatter-format` only as the configured writer for compiled-schema YAML. Its fence
conventions remain compatible, but its generic value materialization does not replace
the softschema portable-value rules.

Portable decoding does not decide whether `2001-13-99` is a valid date.
Use a Pydantic `date`, `time`, `datetime`, or `timedelta` field, or the corresponding
Zod `z.iso.date()`, `z.iso.time()`, `z.iso.datetime()`, or `z.iso.duration()` string
schema, when temporal validity matters.
These model choices are not accept-set equivalents: Pydantic and Zod accept different
spellings and coercions, and Zod datetime options further configure its accepted
strings. A project that needs identical cross-runtime semantics must define and test
aligned model validators or refinements in both implementations.
The `format: date`, `format: date-time`, `format: time`, and `format: duration` values
in a compiled schema are annotations, not structural assertions.
For schema-only lexical rejection, add a portable `pattern` explicitly.
The compiler removes Zod’s intrinsic ISO date, datetime, time, and duration patterns so
structurally corresponding Pydantic and Zod fields produce the same format-only sidecar;
an authored Zod regex remains intact.
The sidecar and its digest therefore describe structural parity, not equality of every
semantic model option.
The validation result’s `values` mapping remains portable strings; host code that needs
native date objects should construct its model explicitly from that mapping.
See [Portable YAML Values](softschema-spec.md#portable-yaml-values) for the exact rule.

For each migration, set `status: soft` or `permissive` initially.
Tighten only after existing instances validate cleanly.

## Playbook: Use softschema with Agents

A coding agent often develops the records, their schema, and their consumers in the same
task. The final structure is least knowable at the beginning, when a hard schema would
require the most guessing.
Give the agent an explicit maturity path so it can preserve useful extensions, learn
from the record corpus, and tighten the boundary without rewriting the workflow.

Use this sequence:

1. **Point the agent at the skill and bundled docs.** When the CLI is installed:

   ```bash
   softschema skill --brief
   softschema docs --list --json
   softschema docs guide
   softschema docs spec
   softschema docs example-artifact
   ```

   These commands work from the installed package; no source checkout is needed.

2. **Choose the artifact profile separately from the schema.** Use the standard
   `frontmatter-md` profile when provenance, interpretation, or other prose should
   travel with the payload.
   Use `pure-yaml` when the structured record stands on its own.
   The Markdown body is optional and never a source of consumed values.

3. **Name consumers and model only the stable core.** List the fields read by each code
   path, agent step, QA check, report, or target system.
   Start with `status: soft`, then add a model and use `permissive` when field names and
   types are stable enough to validate.
   Keep uncertain YAML extensions outside the contract, and keep contextual prose in the
   body when using `frontmatter-md`.

4. **Refine the records and schema together.** Inspect validation results and the corpus
   before adding requirements.
   Normalize existing records, add optional fields, and introduce a required field only
   when producers can supply it and consumers need it.
   Changing the schema does not require changing the Markdown body.

5. **Validate and repair at each handoff.** Run `softschema validate --repair ...`
   immediately after an agent writes an artifact and return the JSON result to the
   agent. `--repair` quotes a scalar that made the document unparsable and retypes one
   the contract wants as a string, writes the file, and then validates — so the
   producing agent sees the same verdict its consumer will, while it is still in a
   position to fix what remains.
   Plain `validate` stays read-only, and `--check-repair` reports what would change
   without writing, which is what a gate runs against an artifact under review.
   Structural and semantic failures are separate.
   For a structural repair, match `kind`, `code`, and `path`; records for missing or
   undeclared properties also include `property`. Do not parse `message`; see
   [Matching on structural error records](softschema-spec.md#matching-on-structural-error-records).

6. **Make software consume the same boundary.** Indexes, ledgers, dashboards, importers,
   and summaries should read YAML only and be regenerated rather than maintained as a
   second source of truth.

7. **Enforce when extensions become errors.** Set `status: enforced` once the compiled
   schema should reject undeclared fields.
   If the data will enter a database, API, or other fixed system, validate against the
   aligned contract immediately before that handoff.

## Playbook: Record a Research Loop

A research loop is any process that repeatedly proposes an idea, measures it, and
decides: optimizing a program’s performance, tuning prompts against an eval, comparing
libraries. Each iteration produces a record with two halves.
An accept rule and a roll-up report must read the numbers, while the hypothesis and the
interpretation are prose that does not fit fixed fields.
The failures are worth as much as the successes, but only if they stay findable.

Give each iteration one artifact.
Promote the values the loop’s own tooling consumes; leave the reasoning in the body:

```markdown
---
softschema:
  contract: myproj.perf:Experiment/v1
  schema: experiment.schema.yaml
  envelope: experiment
  status: enforced
experiment:
  id: exp-012
  hypotheses:
    - H7
  method:
    control: serial directory walk
    candidate: bounded parallel producer
    trials: 12
  results:
    - job: cold-scan
      metrics:
        wall_ns:
          change_pct: -12.0
          ci95_low_pct: -16.5
          ci95_high_pct: -8.4
  verdict:
    decision: accepted
    reason: Interval clear of zero and past the 3% bar for 40 lines of code.
---
# Bounded parallel producer

## Hypothesis

The walk is serial, so one core works while nine idle. Feeding a single index consumer
from a bounded pool of directory readers should cut wall time several-fold.

## What the numbers said

The interval is clear of zero at every trial count we ran, and total CPU stayed flat,
so the gain is parallelism rather than less work.

## Verdict

**ACCEPTED:** the paired median beats the 3% bar and the change adds no new failure
mode.
```

This pattern comes from a real loop of 51 CLI performance experiments, whose entire rig
is a model, a recorder, and a regenerated ledger.
Four habits make the record compound rather than accumulate:

- **Compile the contract from a model.** The Pydantic (or Zod) model is the source of
  truth, and the model’s field descriptions become the documentation every artifact
  ships with. Run `--check` in CI to catch drift:

  ```bash
  softschema compile myproj.perf.experiment:Experiment \
    --out experiment.schema.yaml \
    --contract myproj.perf:Experiment/v1 --check
  ```

- **Record measurements mechanically; ask the operator only for judgment.** A small
  recorder lifts medians and intervals straight from the raw run output into the
  frontmatter, then prompts for what a measurement cannot supply: the hypothesis, the
  complexity cost, the verdict, and one sentence of reasoning.
  Numbers that are never retyped are never mistyped.

- **Regenerate the ledger from validated artifacts.** The roll-up report is a view, not
  a document: it reads each payload through `softschema validate`, so an artifact that
  stops matching the contract fails the build instead of quietly contributing a wrong
  row. Because `decision: rejected` is an ordinary value rather than a note buried in
  prose, the ledger can also list the dead ends nobody should re-run.

- **Let the record be the loop’s memory.** An agent resuming the loop months later reads
  back what was tried and why it was dropped without re-running anything, so the loop
  survives the session that produced it.

## Playbook: Express Cross-Field Rules

This playbook is an advanced one, and most soft schemas never need it: when each field
stands on its own, declare the fields and stop.
Reach for it when a contract is not about individual field types but about how fields
relate: *a record marked `decision: abandoned` must also say what it cost.* Write that
rule in the schema, with a plain JSON Schema conditional, rather than in a separate
checker:

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id: example.research:Experiment/v1
type: object
required: [decision]
properties:
  decision:
    enum: [pending, adopted, abandoned]
  budget_spent:
    type: number
allOf:
- if:
    properties:
      decision:
        const: abandoned
    required: [decision]
  then:
    required: [budget_spent]
```

Under `enforced`, this behaves as follows; every row was verified against both engines:

| Record | Result | Why |
| --- | --- | --- |
| `{decision: pending}` | valid | the matcher does not fire, so the rule imposes nothing |
| `{decision: abandoned, budget_spent: 12.5}` | valid | the rule fires and is satisfied |
| `{decision: abandoned}` | invalid: `required property 'budget_spent' is missing` | the rule fires; the error names the field the author forgot |
| `{decision: pending, bogus: 1}` | invalid: `property 'bogus' is not allowed` | undeclared properties are still rejected in a composed schema |

The third row is the point: the error is actionable, not a generic complaint about
`allOf`.

Three mechanics make this work.
They are worth understanding, because each one is a place where a plausible-looking
alternative silently breaks the schema.

**1. The `if` block is a matcher, not a declaration.** It describes *which documents the
rule applies to*, not what they may contain.
So the validator never closes it.
If it did, `{decision: abandoned}` would stop matching the `if`; the document has no
other properties for a closed matcher to accept, and the conditional would quietly never
fire. You would not get an error; you would get a rule that does nothing.

**2. Reject undeclared properties at the composition root, not inside the branches.** A
branch cannot see what its siblings declare, so inserting the rule in a branch would
reject their keys. Only the root sees all of them.

**3. The root closes with `unevaluatedProperties`, which is annotation-aware.** It
admits any property that some subschema actually evaluated, wherever that subschema
sits. In the schema above `budget_spent` is declared in the root’s own `properties`, so
the lexical `additionalProperties` would admit it too; the difference does not show yet.
It shows the moment a declaration moves into a branch, which is what happens as a schema
grows:

```yaml
allOf:
- if:
    properties: {decision: {const: abandoned}}
    required: [decision]
  then:
    required: [budget_spent]
    properties:
      writeoff_reason: {type: string}     # declared only in the branch
```

`unevaluatedProperties` admits `writeoff_reason` on an abandoned record, because the
`then` branch evaluated it.
`additionalProperties` at the root would not: it sees only the root’s own `properties`
and rejects a key the schema plainly declares.
The admission is success-sensitive: `{decision: pending, writeoff_reason: n/a}` is
rejected because the `then` branch does not apply and no successful schema evaluates
`writeoff_reason` for that record.

One profile rule comes with the annotation model.
Python `jsonschema` and Ajv do not expose condition-matcher annotations consistently in
every shape, so matcher fields must also be unconditionally evaluated at the object
being closed. Declare anything you match on there; `decision` above is declared at the
root for exactly this reason.
Otherwise enforced validation returns `enforcement_unsupported` with reason
`conditional_annotation_scope`.

This keeps the schema as the single statement of the contract.
Reimplementing cross-field rules in a separate checker is exactly the split soft schemas
exist to avoid: two places to update, and only one of them runs in CI.

For the full derivation behind these mechanics—why annotations rather than lexical
siblings decide what counts as declared, what Draft 2020-12 guarantees, and where Python
`jsonschema` and Ajv actually differ—see the research brief,
[JSON Schema Composition, Field Dependencies, and Undeclared Properties](https://github.com/jlevy/softschema/blob/main/docs/project/research/research-2026-08-23-json-schema-composition-and-enforcement.md).
The [spec](softschema-spec.md#rejecting-undeclared-properties-under-enforced) states the
normative rules and the support matrix.

## Common Mistakes

- **Parsing a Markdown body.** Body tables and prose exist for human readers.
  Tools that try to extract structured values from them break the moment a human edits
  the surrounding prose.
- **Hardening too early.** Going straight to `enforced` on a brand-new schema makes
  every extension or authoring variation a failure.
  Start with `soft` or `permissive`; enforce once undeclared fields indicate integration
  errors rather than useful variation.
- **Declaring multiple payload envelopes.** A softschema artifact may designate at most
  one envelope key beside `softschema:`; a `pure-yaml` artifact can also use no
  envelope. Splitting a payload across two envelopes forces every caller to disambiguate.
  (Unrelated top-level keys like `title:` or `tags:` are fine; the anti-pattern is
  multiple keys that all carry payload values softschema is supposed to validate.)
- **Using an implementation name as the contract ID.** Contract IDs name payload
  contracts, not Python classes or Zod exports.
  Bind a contract to a model or compiled schema in standard metadata or host
  configuration; keep language-specific resolution details in the host.
- **Adding a contract with no consumer.** A `soft` convention can precede validation,
  but it still coordinates a producer and a consumer.
  If nobody reads the YAML payload, a contract ID is decoration.
- **Formalizing fields no consumer needs.** Keep uncertain YAML values as extension
  fields until their meaning stabilizes.
  In a Markdown artifact, leave background, analysis, and caveats in the body unless a
  code path, QA check, or aggregation needs a structured value.

## Relationship to the Packages

Two interchangeable packages implement the same language-neutral contract with
Python/Pydantic and TypeScript/Zod.
The Python public surface:

- `Contract`: maps a contract ID to a Pydantic model and optional compiled JSON Schema.
- `Contracts`: host-owned mapping from contract IDs to contracts.
- `validate_artifact(path, contract_id=..., registry=...)`: validates a file at a
  boundary; returns a structured `ArtifactValidationResult` with separate `structural`
  and `semantic` reports.
- `validate_values(values, model=..., schema=...)`: validates a values dict produced by
  any consumer (frontmatter, body-form runtime, structured-output adapter, hand-written
  fixture).
- `compile_model(model_cls, out_path, contract_id=..., schema_id=...)`: emits a
  deterministic JSON Schema YAML file.
  The required contract ID names the payload; the optional schema ID is a separate JSON
  Schema resource URI.

The TypeScript package mirrors this surface (`validateArtifact`, `validateValues`,
`compileSchema`) with Zod models; both CLIs expose the same commands.

The CLI mirrors the library: `softschema validate`, `softschema compile`,
`softschema inspect`, `softschema generate`, `softschema docs`, `softschema skill`.

A host application typically registers complete contracts during startup and validates
artifacts at file boundaries:

```python
from pathlib import Path

from softschema import Contract, Contracts, SchemaStatus, validate_artifact

def build_registry() -> Contracts:
    registry = Contracts()
    registry.register(
        Contract(
            id="mycorp.docs:IncidentReview/v1",
            model=IncidentReview,
            envelope_key="incident",
            status=SchemaStatus.permissive,
            schema_path=Path("schemas/incident-review.v1.schema.yaml"),
        )
    )
    return registry

registry = build_registry()
result = validate_artifact(
    Path("docs/incidents/2026-04-12.md"),
    contract_id="mycorp.docs:IncidentReview/v1",
    registry=registry,
)
assert result.ok
```

When the registered contract does not pin `schema_path` or `envelope_key`,
`validate_artifact` honors the document’s `softschema.schema` and `softschema.envelope`
as fallbacks.

The same contract ID could be validated by a Zod schema in TypeScript, a JSON Schema
compiled schema in any language, a database record, or a hand-written validator.
For Python-specific module layout, public API decisions, and dependency boundary, see
[Python Package Design](softschema-python-design.md).

## Further Reading

- [softschema Spec](softschema-spec.md): exact artifact format and validation
  expectations.
- [Python Package Design](softschema-python-design.md): Python module layout, public
  API, and implementation decisions.
- [TypeScript Package Design](softschema-typescript-design.md): the Zod port and the
  Python ↔ TypeScript API parity table.
- [Movie Page Example](../examples/movie_page/README.md): the complete public example
  backing the snippets above.
- [JSON Schema Composition, Field Dependencies, and Undeclared Properties](https://github.com/jlevy/softschema/blob/main/docs/project/research/research-2026-08-23-json-schema-composition-and-enforcement.md):
  advanced background, needed only for composed or dependent schemas: JSON Schema from
  first principles, the Draft 2020-12 annotation model, and the measured Python
  `jsonschema` and Ajv behavior behind the support matrix.
- [Installation](installation.md), [Development](development.md), and
  [Publishing](publishing.md): workflow docs.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
