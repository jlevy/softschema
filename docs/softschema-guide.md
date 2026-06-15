# softschema Guide

Soft schemas are a practice for adding structure gradually to artifacts that mix human
context and machine-readable values.
This guide is the operational reference for humans and coding agents adopting the
pattern.

For the exact file format and validation rules, see
[softschema Spec](softschema-spec.md).
Two interchangeable implementations ship here, at exact behavioral parity: see
[Python Package Design](softschema-python-design.md) and
[TypeScript Package Design](softschema-typescript-design.md).

## Quick Start for Agents

To set up softschema in a repository with an agent, tell the agent:

> Run `uvx softschema@latest --help` (for the Python implementation) or
> `npx softschema@latest --help` (for the Node implementation) and follow the
> instructions to set up softschema for this repo as a skill.

The help output points the agent to the repo-local skill install command and the bundled
docs it should read next.

## What softschema Is

A **soft schema** is structure added to a document gradually, rather than imposed all at
once. The term is relative to a *hard* schema: instead of declaring a rigid contract
before any data exists and rejecting anything that doesn’t fit, you start with readable
prose and promote values into validated structure only as a consumer needs them.

This matters most for artifacts that mix human context with machine-readable values,
such as a Markdown document with a block of YAML frontmatter.
The prose carries background, judgment, and caveats; the YAML carries the few values
code reads. Either side can grow at any time: a human or agent can add more context to
the prose, promote another value into YAML, or raise how strictly that value is
validated, all without rewriting the artifact.

Structure is a tradeoff.
It makes values reliable for code and lets validation catch errors at a boundary, but it
costs authoring effort and can force false precision on content that isn’t settled.
Soft schemas let a project move along that spectrum field by field, picking the point
that fits the application instead of committing to all-prose or all-data up front.

**Soft schemas** name the general practice.
**softschema** is the implementation in this repository: conventions and tools for the
Markdown-plus-YAML case, shipped as two interchangeable packages held to exact
behavioral parity, Python/Pydantic and TypeScript/Zod, that validate the YAML payload
against a named contract.
The practice is language neutral; another project could implement it with any of JSON
Schema, database records, or hand-written validators.

## When to Use It

Reach for softschema when all three of these hold:

- A human or agent produces the document and the content reads like a document.
- A piece of code, a QA check, or an aggregation needs to consume a few specific values
  from it.
- You want the document to stay readable as the values are formalized.

A common case is the file artifacts that pass between steps of an agent process or
pipeline.
Each artifact mixes the prose context one step produces with the few structured
values the next step consumes; softschema keeps both in one file and validates the
consumed values at the handoff.

Skip softschema when:

- The artifact is already pure structured data (use JSON Schema directly).
- No downstream consumer reads structured values from the document (a convention is
  enough; you don’t need a contract).
- The values change shape every time the document is written (the shape isn’t stable
  enough to name a contract yet).

The promotion path softschema fits into:

```text
prose
  → expected sections and vocabulary       (convention only, no contract)
  → YAML/frontmatter values for consumed fields  (soft → permissive)
  → schema validation at boundaries        (enforced)
  → pure data or deterministic code        (no body left to keep)
```

You can stop at any step.
Many useful artifacts stay in the middle indefinitely.

## The Basic Artifact Pattern

Markdown with YAML frontmatter containing a `softschema` block (the self-description
quartet: `contract`, `schema`, `envelope`, `status`) and one payload envelope key.
Additional frontmatter keys (such as `title`, `description`, or `tags` for a static-site
generator, indexer, or other host convention) are fine and ignored by softschema:

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
   (validate known fields, allow unknown).
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

## Playbook: Choose Which Values Belong in YAML

The hardest call in adoption is “what goes in YAML, what stays prose?”
Use the promotion path step by step:

**Step 1: prose only.** The artifact has no contract, no frontmatter, just a Markdown
body. This is fine when no code or aggregation reads the document.

**Step 2: conventions.** Add a `## Summary` section, a glossary, or a fixed set of
expected headings. No validation, no frontmatter.
Good for human review consistency.
Stay here until a consumer actually reads a value out.

**Step 3: frontmatter values.** As soon as one consumer needs a specific value, promote
that field (and only that field) into YAML frontmatter under an envelope key.
Add `softschema.contract` and `status: soft`. The rest of the document stays prose.

**Step 4: schema validation at boundaries.** When the consumer has been burned by a
missing or malformed value, add a Pydantic model (or compiled schema), set
`status: permissive`, and validate at file boundaries.
Bugs that used to silently break the consumer now fail loudly.

**Step 5: enforced.** When the artifact is consistently good and unknown fields indicate
real authoring bugs, flip `status: enforced`: the validator then rejects undeclared
fields at the structural boundary (object schemas that are silent about
`additionalProperties` are treated as closed; an explicit `additionalProperties` in the
schema still wins). Setting the source model to `extra="forbid"` additionally compiles
that strictness into the compiled schema itself and enforces it at the semantic layer.

**Step 6: pure data.** If the body has shrunk to nothing useful and the artifact is read
more by code than by humans, retire the Markdown wrapper and switch to a YAML or JSON
file. The contract ID stays; only the shell changes.

A field is ready to promote when: a consumer extracts it, the value type is stable, and
emitting it consistently is easier than parsing it from prose.

## Playbook: Inline Frontmatter vs. Companion Data

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

The first Python release supports compiled schemas (the generated JSON Schema YAML
files) but does not implement a generic companion-data loader.
A host project can define its own companion-data convention and resolve the companion
data path before calling `validate_values()`. Don’t invent a generic companion-data DSL
until two artifacts need it.

## Playbook: Add Python Validation

Wire a Pydantic model to a contract and validate at file boundaries:

1. **Define the model.** One Pydantic class per envelope payload, with `extra="forbid"`
   on nested classes when the structure is settled.

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
uv add --dev softschema==0.2.0

# Node
npm i -D softschema@0.2.0
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
  A simple glob validates an entire directory:

  ```bash
  for f in docs/artifacts/*.md; do
    softschema validate “$f”
  done
  ```

  Override flags (`--schema`, `--envelope`, `--model`) are still available when an
  artifact does not self-describe or the host needs to override a binding.

For a full GitHub Actions snippet and a `pre-commit` hook example, see the “Continuous
integration” section of [docs/development.md](development.md).

## Playbook: Migrate an Existing Artifact

Take an artifact that doesn’t fit the canonical shape and bring it in line.

The canonical v0.2 shape is:

- A `softschema:` block (the self-description quartet: `contract`, `schema`, `envelope`,
  `status`) plus a designated envelope key at the top level.
- All consumed values live under the envelope key.
- Body prose is reader-facing only.

Additional top-level keys (such as `title:`, `description:`, `tags:`, `pinned:`, or
other host-specific frontmatter conventions) are allowed and are not interpreted by
softschema.
Only the `softschema` block and the envelope key are softschema’s concern, so
an artifact can mix softschema with whatever metadata a static-site generator, indexer,
or other tool already expects.

Common before/after migrations:

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

For each migration, set `status: soft` or `permissive` initially.
Tighten only after existing instances validate cleanly.

## Playbook: Use softschema with Agents

softschema is built for documents that humans and coding agents both write.
A few patterns help agents do the right thing:

- **Point the agent at the skill and docs.** When the CLI is installed:

  ```bash
  softschema skill --brief
  softschema docs --list --json
  softschema docs guide
  softschema docs spec
  softschema docs example-artifact
  ```

  These commands print bundled material from the installed wheel; no source checkout is
  needed.

- **Tell the agent to write YAML, not body tables.** The most common failure mode is an
  agent that adds nicely-formatted Markdown tables to the body instead of populating the
  YAML payload. The rule is one-line: structured values go in YAML; the body is
  reader-facing only.

- **Run validation in the agent’s feedback loop.** When an agent emits an artifact,
  immediately call `softschema validate ...` and feed the structured error report back.
  Validation failures named in JSON are more actionable than free-text “your output was
  wrong.”

- **Start permissive, then enforce.** When piloting agent-authored artifacts, set
  `status: permissive`. Once the agent emits consistently good documents, flip to
  `enforced`.

## Common Mistakes

- **Parsing the Markdown body.** Body tables and prose exist for human readers.
  Tools that try to extract structured values from them break the moment a human edits
  the surrounding prose.
- **Hardening too early.** Going straight to `enforced` on a brand-new schema makes
  every agent-authored slip a failure.
  Start `permissive` and graduate once the failure pattern is real bugs, not minor
  variance.
- **Splitting a payload across multiple envelopes.** A softschema artifact has a single
  envelope key beside `softschema:`. Splitting payload across two envelopes forces every
  caller to disambiguate.
  (Unrelated top-level keys like `title:` or `tags:` are fine; the anti-pattern is
  multiple keys that all carry payload values softschema is supposed to validate.)
- **Putting implementation details in the artifact.** Resolver settings, compiled-schema
  paths, language identifiers, and migration state belong in host configuration, not in
  authored documents.
- **Adding a `softschema:` block to artifacts no one validates.** A contract ID without
  a consumer is decoration.
  Add structure because something reads it.
- **Promoting prose that no consumer reads.** Leave background, analysis, and caveats as
  prose. Promote a value only when a code path, QA check, or aggregation reads it.

## Relationship to the Packages

Two interchangeable packages implement the language-neutral pattern at exact behavioral
parity, Python/Pydantic and TypeScript/Zod.
The Python public surface:

- `Contract`: maps a contract ID to a Pydantic model and optional compiled JSON Schema.
- `Contracts`: host-owned mapping from contract IDs to contracts.
- `validate_artifact(path, contract_id=..., registry=...)`: validates a file at a
  boundary; returns a structured `ArtifactValidationResult` with separate `structural`
  and `semantic` reports.
- `validate_values(values, model=..., schema=...)`: validates a values dict produced by
  any consumer (frontmatter, body-form runtime, structured-output adapter, hand-written
  fixture).
- `compile_model(model_cls, out_path)`: emits a deterministic JSON Schema YAML file with
  canonical-JSON hashing for drift checks.

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
- [Installation](installation.md), [Development](development.md), and
  [Publishing](publishing.md): workflow docs.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
