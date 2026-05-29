# Softschema Guide

Soft schemas are a practice for adding structure gradually to artifacts that mix human
context and machine-readable values.
This guide is the operational reference for humans and coding agents adopting the
pattern.

For the exact file format and validation rules, see
[Softschema Spec](softschema-spec.md).
For the Python implementation, see [Python Package Design](softschema-python-design.md).

## What Softschema Is

A **soft schema** is structure added to a document gradually, rather than imposed all at
once. The term is relative to a *hard* schema: instead of declaring a rigid contract
before any data exists and rejecting anything that doesn’t fit, you start with readable
prose and promote values into validated structure only as a consumer needs them.

This matters most for artifacts that mix human context with machine-readable values, such
as a Markdown document with a block of YAML frontmatter. The prose carries background,
judgment, and caveats; the YAML carries the few values code reads. Either side can grow at
any time: a human or agent can add more context to the prose, promote another value into
YAML, or raise how strictly that value is validated, all without rewriting the artifact.

Structure is a tradeoff. It makes values reliable for code and lets validation catch
errors at a boundary, but it costs authoring effort and can force false precision on
content that isn’t settled. Soft schemas let a project move along that spectrum field by
field, picking the point that fits the application instead of committing to all-prose or
all-data up front.

**Soft schemas** name the general practice. **Softschema** is the implementation in this
repository: conventions and tools for the Markdown-plus-YAML case, with a Python package
that validates the YAML payload against a named contract. The practice is
language-neutral; another project could implement it with TypeScript, Zod, JSON Schema,
database records, or hand-written validators.

## When To Use It

Reach for softschema when all three of these hold:

- A human or agent produces the document and the content reads like a document.
- A piece of code, a QA check, or an aggregation needs to consume a few specific values
  from it.
- You want the document to stay readable as the values are formalized.

A common case is the file artifacts that pass between steps of an agent process or
pipeline. Each artifact mixes the prose context one step produces with the few structured
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

Markdown with YAML frontmatter, one payload envelope key beside `softschema`:

```markdown
---
softschema:
  contract: example.movies:MoviePage/v1
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

A short prose summary, optionally followed by reader-facing tables that mirror the
YAML for scanning.
```

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

## Playbook: Adopt Softschema For An Existing Markdown Artifact

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

## Playbook: Choose Which Values Belong In YAML

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
missing or malformed value, add a Pydantic model (or JSON Schema sidecar), set
`status: permissive`, and validate at file boundaries.
Bugs that used to silently break the consumer now fail loudly.

**Step 5: enforced.** When the artifact is consistently good and unknown fields indicate
real authoring bugs, flip `status: enforced` and set the source model to
`extra="forbid"`.

**Step 6: pure data.** If the body has shrunk to nothing useful and the artifact is read
more by code than by humans, retire the Markdown wrapper and switch to a YAML or JSON
file. The contract ID stays; only the shell changes.

A field is ready to promote when: a consumer extracts it, the value type is stable, and
emitting it consistently is easier than parsing it from prose.

## Playbook: Inline Frontmatter Vs Data Sidecar

The rule of thumb is **inline-small, sidecar-large**:

- **Inline (frontmatter)** when the structured payload is a few dozen fields or a
  handful of small nested objects.
  Authors can see everything in one file; review comments land on the right line;
  readers don’t context-switch.
- **Data sidecar** when the payload is large, machine-generated, or distracting to a
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

A sidecar is right for a large machine-generated payload, such as a backtest result:

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
summary). The full payload lives in the sidecar.

The first Python release supports schema sidecars (the generated JSON Schema YAML files)
but does not implement a generic data-sidecar loader.
A host project can define its own data-sidecar convention and resolve the sidecar path
before calling `validate_values()`. Don’t invent a generic sidecar DSL until two
artifacts need it.

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

2. **Compile a JSON Schema sidecar** so non-Python consumers can validate too:

   ```bash
   uv run softschema compile mycorp.docs.incident:IncidentReview \
     --contract mycorp.docs:IncidentReview/v1 \
     --out schemas/incident-review.v1.schema.yaml
   ```

3. **Register a `SoftschemaBinding`** in your host startup:

   ```python
   from softschema import SoftschemaBinding, SoftschemaRegistry, SoftschemaStatus

   def build_registry() -> SoftschemaRegistry:
       registry = SoftschemaRegistry()
       registry.register(
           SoftschemaBinding(
               contract_id="mycorp.docs:IncidentReview/v1",
               model=IncidentReview,
               envelope_key="incident",
               status=SoftschemaStatus.permissive,
               schema_path=Path("schemas/incident-review.v1.schema.yaml"),
           )
       )
       return registry
   ```

4. **Validate at the boundary** (anywhere your host opens a file from disk, a queue, or
   an upload):

   ```python
   from softschema import validate_artifact
   result = validate_artifact(path, contract_id=..., registry=build_registry())
   if not result.ok:
       handle_validation_failure(result)
   ```

5. **Tighten over time.** Start `permissive`; flip to `enforced` and add
   `extra="forbid"` once authoring is consistently clean.

The `result` object reports `structural` (JSON Schema) and `semantic` (Pydantic) errors
separately, so callers can distinguish “shape was wrong” from “cross-field invariant
failed” without parsing error strings.

## Playbook: Keep Schema Tables In Sync With Generated Sections

When a controlled vocabulary or field list appears in two places (a schema and a runbook
table), it will drift.
Generated sections solve this by making the runbook table a deterministic projection of
the schema.

Wrap any Markdown block you want regenerated:

```markdown
<!-- softschema:generated kind="enum_table" contract="schemas/incident.schema.yaml" -->
| Field | Allowed values |
| --- | --- |
| `severity` | SEV-1, SEV-2, SEV-3 |
<!-- /softschema:generated -->
```

Then re-render in place:

```bash
uv run softschema generate path/to/runbook.md
```

CI runs the same command with `--check`, which exits non-zero if any block has drifted
from the current schema:

```bash
uv run softschema generate path/to/runbook.md --check
```

Available `kind` values:

- `enum_table` — one row per enum field in the schema (`Field`, `Allowed values`).
- `field_list` — one bullet per top-level field (name, type, required, description).
- `vocab` — enum values for one specific field; requires a `pointer="/properties/foo"`
  attribute.

A worked example lives in
[examples/movie_page/README.md](../examples/movie_page/README.md); the “Schema Enums”
section is regenerated from the movie schema.

## Playbook: Validate In CI

Two checks belong in CI:

- **Sidecar drift check** — fail the build when a committed schema sidecar is out of
  sync with the source model.

  ```bash
  uv run softschema compile mycorp.docs.incident:IncidentReview \
    --contract mycorp.docs:IncidentReview/v1 \
    --out schemas/incident-review.v1.schema.yaml --check
  ```

- **Artifact validation** — fail the build when any artifact under version control
  doesn’t validate.

  ```bash
  uv run softschema validate path/to/artifact.md \
    --model mycorp.docs.incident:IncidentReview \
    --schema schemas/incident-review.v1.schema.yaml
  ```

For a full GitHub Actions snippet and a `pre-commit` hook example, see the “Continuous
integration” section of [docs/development.md](development.md).

## Playbook: Migrate An Existing Artifact

Take an artifact that doesn’t fit the canonical shape and bring it in line.

The canonical v0.1 shape is:

- Exactly one `softschema:` block plus exactly one envelope key at the top level.
- All consumed values live under the envelope key.
- Body prose is reader-facing only.

Common before/after migrations:

**Multiple top-level keys → single envelope.**

Before (multiple keys at the root, no envelope):

```yaml
---
title: Spirited Away
release_year: 2001
ratings:
  ...
---
```

After:

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

## Playbook: Use Softschema With Agents

Softschema is built for documents that humans and coding agents both write.
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
- **Multiple top-level payload keys.** The canonical shape has exactly one envelope key
  beside `softschema:`. Multiple keys force every caller to disambiguate.
- **Putting implementation details in the artifact.** Resolver settings, sidecar paths,
  language identifiers, and migration state belong in host configuration, not in
  authored documents.
- **Adding a `softschema:` block to artifacts no one validates.** A contract ID without
  a consumer is decoration.
  Add structure because something reads it.
- **Promoting prose that no consumer reads.** Leave background, analysis, and caveats as
  prose. Promote a value only when a code path, QA check, or aggregation reads it.

## Relationship To The Python Package

The Python package is one convenience implementation of the language-neutral pattern.
Public surface:

- `SoftschemaBinding` — maps a contract ID to a Pydantic model and optional JSON Schema
  sidecar.
- `SoftschemaRegistry` — host-owned mapping from contract IDs to bindings.
- `validate_artifact(path, contract_id=..., registry=...)` — validates a file at a
  boundary; returns a structured `ArtifactValidationResult` with separate `structural`
  and `semantic` reports.
- `validate_values(values, model=..., schema=...)` — validates a values dict produced by
  any consumer (frontmatter, body-form runtime, structured-output adapter, hand-written
  fixture).
- `compile_model(model_cls, out_path)` — emits a deterministic JSON Schema YAML sidecar
  with canonical-JSON hashing for drift checks.

The CLI mirrors the library: `softschema validate`, `softschema compile`,
`softschema inspect`, `softschema docs`, `softschema skill`.

A host application typically registers complete bindings during startup and validates
artifacts at file boundaries:

```python
from pathlib import Path

from examples.movie_page.host_integration import build_movie_page_registry
from softschema import validate_artifact

registry = build_movie_page_registry()
result = validate_artifact(
    Path("examples/movie_page/spirited-away.md"),
    contract_id="example.movies:MoviePage/v1",
    registry=registry,
)
assert result.ok
```

The same contract ID could be validated by a Zod schema in TypeScript, a JSON Schema
sidecar in any language, a database record, or a hand-written validator.
For Python-specific module layout, public API decisions, and dependency boundary, see
[Python Package Design](softschema-python-design.md).

## Further Reading

- [Softschema Spec](softschema-spec.md) — exact artifact format and validation
  expectations.
- [Python Package Design](softschema-python-design.md) — Python module layout, public
  API, and implementation decisions.
- [Movie Page Example](../examples/movie_page/README.md) — the complete public example
  backing the snippets above.
- [Installation](installation.md), [Development](development.md), and
  [Publishing](publishing.md) — workflow docs.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
