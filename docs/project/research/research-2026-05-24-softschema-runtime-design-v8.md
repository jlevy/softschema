---
title: softschema — clean, simple design (v8)
description: softschema is a schema-bundle and generated-sections library for Markdown artifacts whose structured values are validated by Pydantic and JSON Schema. It has one native document profile (frontmatter values plus narrative body). Phase 0 ships compile, structural validate, semantic validate, validate-values, and generate-sections. Body-form workflows, manifest sidecar, patches, mirrors, materialization, repair-class issues, and provider adapters stay reserved.
author: Joshua Levy + Claude
---
# Research: softschema — Clean, Simple Design (v8)

**Status:** Design proposal.
The current public Python package implements a subset of this design; the remaining
surface is tracked in the public-readiness plan.

This is an evolving design document.
It describes the target shape of softschema as a schema-bundle and validation library
for Markdown/YAML artifacts.
Worked examples are generic illustrations only and not tied to any specific domain.

## Architecture

The name “softschema” can mislead.
It is not weak schema validation.
The design is the opposite: **hard schema, soft authoring**. The contract is strict
(Pydantic + JSON Schema, both running with `extra="forbid"` semantics), but the authored
Markdown document remains narrative, editable, and gradually migratable.

```text
Pydantic source models
   ↓ compile
JSON Schema 2020-12 + x-softschema annotations  ←── the schema bundle
   ↓ consumed by
softschema runtime
   - validates Profile A values (structural and semantic, reported separately)
   - regenerates <!-- softschema:generated --> sections
```

softschema core has one native document profile: frontmatter values plus narrative
Markdown. Body-form documents are not a second softschema profile; they are external
runtimes that may export values into softschema validation.
softschema is consumer-agnostic at the values layer: anything that can produce a values
dict (frontmatter parser, body-form runtime, structured-output adapter, hand-written
test fixture) can call `validate_values`. Phase 0 ships only the frontmatter consumer;
other consumers compose without softschema-side changes.

## Core principles

1. **Pydantic models are the source of truth.** In Python projects.
   Other schema sources (Zod, TypeBox, hand-authored JSON Schema) produce the same
   bundle shape; this document targets the Python case.
2. **The JSON Schema sidecar is a portable artifact.** Generated from the model,
   committed to the repo, consumed by validators, generated sections, and cross-language
   tooling.
3. **Cross-field invariants live in `@model_validator`s.** They cannot be cleanly
   expressed in JSON Schema; that is why Pydantic remains canonical and why semantic
   validation requires the Python class.
4. **softschema has one native document profile.** Frontmatter values plus narrative
   Markdown body. No body-binding tags.
   Every artifact in scope for the initial work is this shape.
5. **softschema is consumer-agnostic at the values layer.** `validate_values` takes a
   dict; the dict can come from a frontmatter parser, a body-form runtime, a
   structured-output adapter, or a test fixture.
   softschema does not own any document parser beyond frontmatter.
6. **Generated sections eliminate drift.** Any schema fact that appears in two places
   (controlled vocab in a runbook, enum list in QA code, field map in a judge prompt),
   one of those places is a generated section.
   CI fails on drift.
7. **`x-softschema` is annotation only.** It carries authoring metadata (group, owner,
   tier, instruction, aliases, repair).
   It is not a second validation language.
8. **Phase 0 is small and self-contained.** Compile, validate (structural and semantic),
   validate-values, generate-sections.
   Manifest, patches, mirrors, materialization, repair-class issues, provider adapters,
   and bridges to non-frontmatter consumers all stay reserved.

## What we’re building

```text
Pydantic model
   ↓ compile
JSON Schema sidecar (with x-softschema annotations)
   ↓ consumed by
softschema runtime: validate Profile A values, regenerate <!-- softschema:generated --> sections
```

One artifact per schema in Phase 0:

| Artifact | Owner | Purpose |
| --- | --- | --- |
| `MyDoc.py` (Pydantic) | Engineer | Source of truth for the contract |
| `schemas/my-doc.v1.schema.yaml` | Compiler | JSON Schema with `x-softschema` annotations |

The manifest sidecar (v5/v6 design) is removed from Phase 0. If it returns later, it is
for one of: language-neutral invariant descriptions, migration maps, generated-section
presets too large for `x-softschema`, schema-registry metadata, or provider-adapter
metadata. None of those are Phase 0 needs.

## The Pydantic contract layer

Each field carries metadata that drives prompts, runbook tables, judge prompts, JSON
Schema export, and lifecycle policies.

### `SField` and `x-softschema` metadata

```python
from typing import Any, Literal, TypeAlias
from pydantic import BaseModel, Field


SoftOwner: TypeAlias = Literal["agent", "postprocess", "system", "human"]
SoftTier: TypeAlias = Literal["hard_fact", "constrained", "narrative"]
RepairKind: TypeAlias = Literal["none", "safe_coerce", "suggest_alias"]


class SFieldMeta(BaseModel):
    group: str
    order: int | None = None
    tier: SoftTier | None = None
    owner: SoftOwner = "agent"
    instruction: str | None = None
    examples: list[Any] = Field(default_factory=list)
    aliases: dict[str, list[str]] = Field(default_factory=dict)
    repair: RepairKind = "none"


def SField(
    *,
    description: str,
    group: str,
    owner: SoftOwner = "agent",
    tier: SoftTier | None = None,
    aliases: dict[str, list[str]] | None = None,
    examples: list[object] | None = None,
    instruction: str | None = None,
    repair: RepairKind = "none",
    **field_kwargs,
):
    meta = SFieldMeta(
        group=group,
        owner=owner,
        tier=tier,
        aliases=aliases or {},
        examples=examples or [],
        instruction=instruction,
        repair=repair,
    )
    return Field(
        description=description,
        json_schema_extra={"x-softschema": meta.model_dump(exclude_none=True)},
        **field_kwargs,
    )
```

The shared `TypeAlias`es prevent bad metadata from reaching the schema sidecar and make
`SField` itself self-documenting: an editor that types-checks the call site catches
typos like `owner="agennt"` or `tier="hardfact"` at author time, not at compile time.

Constraints, instructions, enum values, ownership, tiering, and aliases live in one
Python source. The compiler emits `x-softschema` verbatim into the JSON Schema sidecar.

`x-softschema` is annotation-only.
It is consumed by generated-section renderers, by judge-prompt builders, by QA tier
maps, and by agent-facing prompts.
It is *not* used to express validation rules.
Cross-field invariants stay in Pydantic.

### Alias semantics

`aliases` on a field is a controlled-vocabulary repair table: strings the agent might
plausibly emit that should map to canonical enum values.
The runtime treats them as follows:

- An alias with **one** target is exact and may be auto-repaired only when the field’s
  `repair` is `safe_coerce`.
- An alias with **multiple** targets is ambiguous and must produce a *proposed* repair,
  not an automatic rewrite, regardless of `repair` setting.
- Alias matching is case-insensitive and whitespace-normalized unless the field opts out
  via a future `match_strict: true` attribute.
- Aliases are authoring/repair metadata only.
  They do **not** extend the JSON Schema enum; downstream JSON Schema validators will
  still reject the alias string.
  The alias resolution happens in the softschema runtime before validation, or as part
  of a (future) repair pass.

This rule prevents aliases from quietly becoming a second enum language.

### Cross-field invariants

```python
@model_validator(mode="after")
def _direction_matches_move(self) -> "WidgetRecord":
    if self.direction == Direction.up and self.delta_pct < 0:
        raise ValueError(f"direction=up but delta_pct={self.delta_pct}")
    if self.direction == Direction.down and self.delta_pct > 0:
        raise ValueError(f"direction=down but delta_pct={self.delta_pct}")
    return self
```

The runtime translates Pydantic `ValidationError`s into the host system’s existing error
type (e.g. the QA pipeline’s `CheckResult`). v7 deliberately does not introduce a new
`Issue` dataclass with repair classes, proposed patches, source spans, or agent retries.
Pydantic’s structured error model is sufficient for Phase 0.

### Strict by default

```python
model_config = ConfigDict(
    extra="forbid",
    use_enum_values=False,
    validate_assignment=False,
)
```

`extra="forbid"` is the production default.
`validate_assignment=False` is deliberate: cross-field invariants fire at boundary
validation, not on every attribute assignment, so postprocess can mutate multiple fields
atomically before re-validating.

## The JSON Schema sidecar

The compiler produces one file per schema in Phase 0:

```text
schemas/widget-record.v2.schema.yaml
```

JSON Schema 2020-12 serialized as YAML for readability, with `x-softschema` annotations:

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id: urn:example.docs:WidgetRecord:v2
title: WidgetRecordEnvelope

x-softschema:
  generated_from: example_app.schemas.widget_record:WidgetRecordEnvelope
  softschema_version: "0.1"

type: object
required: [record]
properties:
  record:
    $ref: "#/$defs/WidgetRecord"

$defs:
  WidgetRecord:
    type: object
    additionalProperties: false
    required: [record_id, period, outcome, direction, delta_pct, qualitative]
    properties:
      record_id:
        type: string
        pattern: "^WID-[0-9]{3,6}$"
        description: Record identifier.
        x-softschema:
          group: identity
          owner: agent
          tier: hard_fact

      outcome:
        type: string
        enum: [above, below, on_plan, mixed, none, n_a]
        description: Outcome classification.
        x-softschema:
          group: outcomes
          owner: agent
          tier: hard_fact
          aliases:
            "not applicable": [n_a, none]
            "n/a": [n_a, none]
          repair: suggest_alias
```

Plain JSON Schema validators (`jsonschema` in Python, `ajv` in TypeScript) validate
shape.
The softschema runtime additionally reads `x-softschema` for agent metadata, alias
tables, and renderer hints.

### Validator-side note on `x-softschema`

JSON Schema permits extension keywords, but some validator configurations, especially
strict modes, warn or fail on unknown keywords unless explicitly registered.
Consumers must configure their validators to tolerate or register `x-softschema`. The
Phase 0 README documents this for Python (`jsonschema` allows unknown keywords by
default) and TypeScript (`ajv` requires `strict: false` or keyword registration).

### Schema hashing (canonical JSON, not human-formatted YAML)

Schema hashes are load-bearing in Phase 0 because (a) `compile --check` depends on
deterministic sidecar output, and (b) generated-section markers carry a `sha256`
attribute that pins the section to a specific schema revision.
Both must compute the same hash regardless of YAML formatting choices.

The hash is **SHA-256 over a canonical JSON representation**, not over the
human-formatted YAML bytes:

- UTF-8 encoding
- JSON object keys sorted lexicographically at every nesting level
- no insignificant whitespace
- no `generated_at` timestamp (excluded from the hashable representation)
- `x-softschema` annotations included
- numbers in their canonical JSON form (no trailing zeros except for integer
  disambiguation; no `.0` suffix on integers)

The committed sidecar stays YAML for readability.
The hash is computed by serializing the parsed JSON Schema document to canonical JSON
and hashing that byte stream.
Two sidecars that round-trip to the same JSON Schema produce the same hash even if their
YAML formatting differs.

This is the schema-side rule.
Value canonicalization (for instance values in a materialized sidecar) is deferred until
materialization itself lands; see Appendix A.7.

### CI guarantee

```bash
softschema compile <module:Class> --check schemas/<name>.schema.yaml
```

Failure mode: schema drifted from Pydantic source.
Fix: re-run without `--check` and commit.
Generated, but committed.

### Schema reference resolution

Documents reference schemas by either path or URN:

```yaml
# By path (relative to the document)
softschema:
  schema:
    ref: ../../schemas/widget-record.v2.schema.yaml

# By URN (resolved through the repo registry)
softschema:
  schema:
    ref: urn:example.docs:WidgetRecord:v2
```

Generated sections use the same reference forms.

A small repo-level registry (`softschema.yaml` at the repo root) maps URNs to file paths
so every consumer resolves them the same way:

```yaml
# softschema.yaml
schemas:
  urn:example.docs:WidgetRecord:v2: schemas/widget-record.v2.schema.yaml
  urn:example.docs:Checklist:v1: schemas/checklist.v1.schema.yaml
```

Resolution rules:

1. If `ref` is a relative or absolute path, load the file.
   Resolve relative paths against the containing document.
2. If `ref` is a URN, resolve through `softschema.yaml`.
3. If both `ref` (path) and `id` (URN) are supplied on a document, load by path and
   assert that the loaded schema’s `$id` matches the URN. Mismatch is a hard error.

This prevents every generated-section scanner and every validation entry point from
inventing its own resolution logic.

## Profile A: frontmatter values, narrative body

softschema’s one native document profile.

```markdown
---
softschema:
  spec: "0.1"
  schema:
    ref: ../../schemas/widget-record.v2.schema.yaml
  values:
    location: frontmatter
    pointer: /values

values:
  record:
    record_id: WID-001
    period: 2025-Q2
    due_date: 2025-05-01
    outcome: on_plan
    direction: up
    delta_pct: 4.20
    qualitative:
      expected_summary: On-plan baseline result, neutral outlook.
      observed_summary: Operations efficiency expansion.
      counterfactual: Without efficiency gains, the result would be on plan.
      evidence_snippets:
        - source_date: 2025-04-29
          source_type: interview
          observation: Team reported steady throughput improvements.
---
# WID-001 — 2025-Q2 Record

## Why The Result Came In Where It Did

Plain Markdown narrative. The structured data lives in frontmatter; the
body is for prose explanation, not for value capture.
```

Frontmatter holds the values; body is plain Markdown.
No body-binding tags, no body-binding parser, no template linter rules for body
coverage.

### The `softschema:` block policy

| Document state | Policy |
| --- | --- |
| Existing legacy instances | Block optional. Host pipeline resolves schema by file path or callsite. |
| New templates | Block required. The template self-describes its schema. |
| New generated instances | Block required, unless the artifact is intentionally host-bound. |
| CLI invocations | `--schema` and `--model` override document metadata when present. |

This policy lets large legacy corpora stay unchanged while every new artifact is
self-describing.

### The value resolver

The frontmatter value resolver is explicit, not the v6
`frontmatter.get("values", frontmatter)` shorthand:

```python
class ValueResolver(BaseModel):
    kind: Literal["values_key", "frontmatter_root", "host_adapter"]
    pointer: str | None = "/values"
    exclude_keys: list[str] = []
```

| Mode | Use |
| --- | --- |
| `values_key` (default for new docs) | Values live at `pointer` (default `/values`); frontmatter-level metadata is excluded. |
| `frontmatter_root` (legacy mode) | Values live at frontmatter root; metadata keys (e.g., `softschema`) are removed via `exclude_keys` if present. |
| `host_adapter` | The host pipeline supplies a callable that returns the values dict. Used when neither of the above shapes applies. |

For new docs, the canonical shape is:

```yaml
softschema:
  values:
    location: frontmatter
    pointer: /values

values:
  record:
    ...
```

For legacy widget records (today’s `record:` at frontmatter root), the host pipeline
configures `frontmatter_root` with `exclude_keys: ["softschema"]`. The legacy mode is a
compatibility seam, not the public format.

### Validation

softschema treats structural and semantic validation as **two independent engines**,
never folded into each other:

- **Structural** is JSON Schema validation against the sidecar (`jsonschema` in Python,
  `ajv` in TypeScript).
  It is cross-language and works without the Python model class.
  It catches type mismatches, enum violations, missing-required, and shape errors.
- **Semantic** is Pydantic `model_validate` against the model class.
  It runs type validation, field constraints, enum checks, **and** `@model_validator`
  cross-field invariants.
  It is Python-only.

These two engines usually agree on shape but they are not identical.
Pydantic validation is not “JSON Schema validation that happens to be running in
Python.” When both run, they run independently and report independently.

```python
# Structural only (cross-language, works without Python class):
softschema.validate_values(values, schema=schema_yaml_path)

# Semantic (Pydantic; Python-only; runs invariants):
softschema.validate_values(values, model=WidgetRecordEnvelope)

# Both, independently:
softschema.validate_values(values, model=WidgetRecordEnvelope, schema=schema_yaml_path)
```

CLI mappings:

```bash
softschema validate <doc.md> --schema schemas/widget-record.v2.schema.yaml
# JSON Schema structural only

softschema validate <doc.md> --model example_app.schemas.widget_record:WidgetRecordEnvelope
# Pydantic only (validates shape, constraints, and invariants)

softschema validate <doc.md> --schema schemas/widget-record.v2.schema.yaml \
                              --model example_app.schemas.widget_record:WidgetRecordEnvelope
# Runs both engines independently; reports both
```

Result shape always carries both fields:

```yaml
validation:
  structural:
    ok: true
    engine: json_schema
  semantic:
    ok: skipped
    reason: no_pydantic_model
```

When an engine is not requested, its `ok` is `skipped` with a `reason`. Consumers that
see `structural.ok: true` without `semantic.ok: true` know cross-field invariants did
not run.

#### Schema/model mismatch check

When both document metadata (`softschema.schema.ref`) and a `--model` flag are present,
softschema asserts that the model’s generated `$id` matches the document schema `$id`
(the registry URN, if `softschema.yaml` resolves the path).
Mismatch fails the run, unless `--allow-schema-mismatch` is set.
This is a cheap guardrail against operator mistakes (running confidence-record
validation on a widget-record document, etc.).

## Generated sections

The mechanism that eliminates schema-fact duplication across documents.

```markdown
<!-- softschema:generated kind="enum_table" schema="urn:example.docs:WidgetRecord:v2" sha256="..." -->
| Field | Allowed values |
| --- | --- |
| outcome | above, below, on_plan, mixed, none, n_a |
| direction | up, down, mixed, flat |
| evidence_snippets[].source_type | filing, transcript, news, market_data, alt_data |
<!-- /softschema:generated -->
```

### Namespaced markers

Markers carry the `softschema:` namespace.
Generic `<!-- generated -->` is too likely to collide with other tools.
The closing tag matches: `<!-- /softschema:generated -->`.

### Language-aware markers

For non-Markdown targets, use language-appropriate comment syntax.
Do not put HTML comments in Python source.

| Target | Marker |
| --- | --- |
| Markdown | `<!-- softschema:generated ... -->` … `<!-- /softschema:generated -->` |
| Python | `# <softschema:generated kind="..." schema="...">` … `# </softschema:generated>` |
| YAML / TOML | `# softschema:generated kind="..." schema="..."` … `# /softschema:generated` |

For Python, prefer a *fully generated file* over marker blocks inside hand-authored
source. Marker blocks in `.py` are an option, but a standalone module is safer:

```text
example_app/generated/
  __init__.py
  widget_record_constants.py     # entirely owned by softschema; never hand-edited
```

### Section attributes

A generated section needs more than `kind`. The attribute set:

```text
kind             enum_table | field_list | vocab
schema           bundle URN or path
root             JSON Pointer for the entry definition (default "#")
view             named preset (defined in the schema's root x-softschema.views)
include_paths    explicit JSON Pointer list (mutually exclusive with view)
exclude_paths    JSON Pointer list to omit
include_groups   x-softschema.group filter
include_owner    x-softschema.owner filter
include_tier     x-softschema.tier filter
format           markdown_table | markdown_list | plain | yaml | json
sort             schema_order | alphabetical | tier
sha256           hash of the schema bundle that produced the section (informational)
```

Without these, every generated field-list becomes a one-off generator.
With them, presets are reusable across documents.

### Views

Most generated sections in practice need a curated subset of fields (the judge prompt
wants different fields than the runbook controlled-vocab table).
Rather than spread filter attributes across every marker, define **views** in the
schema’s root `x-softschema`:

```yaml
# In the schema YAML:
x-softschema:
  generated_from: example_app.schemas.widget_record:WidgetRecordEnvelope
  softschema_version: "0.1"
  views:
    all_enums:
      kind: enum_table
      include_enums: true
      sort: schema_order
    judge:
      kind: field_list
      include_owner: [agent, postprocess]
      include_groups: [identity, numeric_outcomes, qualitative]
      format: markdown_list
      sort: schema_order
```

A marker with `view="judge"` resolves the preset and applies any additional attributes
on top. Views keep judge prompts and runbooks from accumulating long marker attribute
lists.

### Marker block form for complex attributes

Single-line markers are fine for simple sections:

```markdown
<!-- softschema:generated kind="enum_table" schema="urn:example.docs:WidgetRecord:v2" view="all_enums" -->
```

When attributes get long (`include_paths`, `exclude_paths`, multiple groups, custom
sort), use the block form:

```markdown
<!-- softschema:generated
kind: field_list
schema: urn:example.docs:WidgetRecord:v2
view: judge
format: markdown_list
sort: schema_order
-->
...
<!-- /softschema:generated -->
```

The generator canonicalizes back to whichever form was used in the source.
Both forms are equally valid; agents and humans pick whichever reads better at the call
site.

### Hash semantics

The `sha256` attribute on a generated-section marker records the schema-bundle hash used
to render the section content.
It is checked by `generate-sections --check` and indicates whether the section content
is in sync with the current schema.
It is **not** used to reject the containing Markdown document during normal validation.
A document with a stale generated section is a CI build issue (regenerate and commit),
not a document-validity issue.

### Allowed `kind` values (Phase 0)

| `kind` | Purpose |
| --- | --- |
| `enum_table` | Markdown table of fields and their enums |
| `field_list` | Markdown list of fields and types (judge-prompt style) |
| `vocab` | Plain-text controlled-vocabulary listing |

`example` (renders example instance values from a schema-attached fixture) and
`python_constants` (emits Python source) are **not** Phase 0 kinds.
They are reserved extension points:

- `example` lands when a runbook section that needs generated examples earns the
  fixture-source design (`x-softschema.examples.<name>` block at schema root).
- `python_constants` lands only as a fallback when a consumer cannot read the schema
  bundle via `SchemaView` directly, and even then prefers a fully generated standalone
  Python module (e.g., `example_app/generated/widget_record_constants.py`) rather than
  marker blocks inside hand-authored source.
  For QA in this codebase, `SchemaView` removes the need.

### Generated sections versus mirrors

Generated sections render *schema facts* (enum values, field names, types, controlled
vocabularies). Mirrors render *instance values* (the scenario probability table inside a
prediction record, the price table inside a confidence assessment).
They are different mechanisms.

v7 ships generated sections only.
Mirrors stay deferred.
When a mirror earns its keep, the marker syntax distinguishes them so the two don’t get
conflated:

```text
<!-- softschema:generated kind="schema.enum_table" ... -->     # schema-derived
<!-- softschema:generated kind="value.price_table" ... -->     # instance-derived (future)
```

The `schema.` / `value.` prefix on `kind` keeps the surfaces separable when mirrors
arrive.

### CI integration

```bash
softschema generate-sections [paths...]            # regenerate in place
softschema generate-sections --check [paths...]    # fail nonzero on drift
```

CI runs `--check`. Adding a new enum value to the Pydantic source and forgetting to
regenerate fails the build; rerunning `softschema generate-sections` and committing the
result fixes it.

### What this replaces

| Today | After |
| --- | --- |
| Hand-maintained controlled-vocab tables in `record.template.md` | `kind="enum_table"` generated section |
| Hand-maintained vocab in `generate-record.runbook.md` | `kind="vocab"` generated section |
| Hand-maintained field map in `evals/widget-eval/judge-prompt.md` | `kind="field_list"` generated section |
| Hand-maintained example tables in runbooks | Stay hand-edited in Phase 0; `kind="example"` lands when fixture-source design is earned |
| Hand-maintained enum constants in `qa/rules/widget_rules.py` | QA reads enums via `SchemaView` (see §The minimal runtime API); no Python codegen |

The QA enum-constants case is worth calling out: rather than generate Python constants,
QA reads the schema bundle through `SchemaView` at startup and sources enums from it.
That removes one generated artifact and one drift surface.

## The minimal runtime API

Phase 0 surface, with a clean separation between non-raising report functions and
Pydantic-native convenience:

```python
def compile(model_cls, out_path) -> CompileResult:
    """Emit the JSON Schema sidecar from a Pydantic model class."""

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

    Use this when host code wants Pydantic-native exception-raising behavior. The CLI
    and `validate_values` use the non-raising report path.
    """

def generate_sections(paths: list[Path], *, check: bool = False) -> GenerateResult:
    """Regenerate <!-- softschema:generated --> blocks. With check=True, fail on drift."""
```

Pydantic’s `ValidationError.errors()` already returns structured `loc`, `msg`, `type`,
and `input` fields.
`ValidationReport` wraps those for the structural engine’s output and
for the Pydantic engine’s output, with no new richer `Issue` model in Phase 0.

### `SchemaView`: shared schema reader

QA reads enum values from the sidecar, `compare_records` reads `x-softschema.tier`,
generated sections walk the schema fields.
If each consumer parses JSON Schema independently, the drift problem is recreated
*inside the readers*. Phase 0 ships a small shared schema reader so every consumer goes
through one logic path:

```python
class FieldInfo:
    pointer: str            # JSON Pointer into the schema, e.g. /properties/record/properties/record_id
    name: str               # e.g. "record_id"
    json_type: str          # JSON Schema type
    enum: list[str] | None
    required: bool
    description: str
    softmeta: dict[str, Any]  # the field's x-softschema annotations


class SchemaView:
    """Read-only view over a compiled schema bundle. The single reader QA, compare,
    eval-judge, and generated sections all go through.
    """

    @classmethod
    def load(cls, schema_path: Path) -> "SchemaView": ...
    @classmethod
    def load_urn(cls, urn: str, registry: Path | None = None) -> "SchemaView": ...

    @property
    def root_softmeta(self) -> dict[str, Any]: ...
    @property
    def schema_id(self) -> str: ...
    @property
    def schema_sha256(self) -> str: ...

    def iter_fields(self, *, include_refs: bool = True) -> Iterable[FieldInfo]: ...
    def field(self, pointer: str) -> FieldInfo: ...
    def enum_values(self, pointer: str) -> list[str] | None: ...
    def softmeta(self, pointer: str) -> dict[str, Any]: ...
    def fields_by_group(self, group: str) -> list[FieldInfo]: ...
    def fields_by_owner(self, owner: str) -> list[FieldInfo]: ...
    def fields_by_tier(self, tier: str) -> list[FieldInfo]: ...
    def view(self, name: str) -> "FieldQuery": ...
```

`SchemaView` is what makes “QA imports the schema bundle directly” safe.
Generated sections, QA enum lookups, and `compare_records` tier maps all consume the
same `FieldInfo` shape.

### CLI surface

```bash
# Compile and check
softschema compile <module:Class> --out <schema.yaml>
softschema compile <module:Class> --check <schema.yaml>

# Validate (independent engines; either or both)
softschema validate <doc.md> --schema <schema.yaml>                  # structural only
softschema validate <doc.md> --model <module:Class>                  # semantic (Pydantic)
softschema validate <doc.md> --schema <schema.yaml> --model <module:Class>  # both

# Validate against pre-extracted values
softschema validate-values <values.yaml> --model <module:Class>
softschema validate-values <values.yaml> --pointer /values --model <module:Class>

# Generate
softschema generate-sections [paths...]
softschema generate-sections --check [paths...]

# Debug
softschema schema-info <schema.yaml> --enum-table        # human-readable schema dump
softschema schema-info <schema.yaml> --view judge        # preview a named view
```

`validate-values` expects the values object at the YAML root by default.
Use `--pointer /values` when validating a wrapped file (e.g., a materialized sidecar
with the `softschema/values` envelope).
This avoids confusion between authored document frontmatter, materialized sidecars, and
raw extracted values.

`--allow-schema-mismatch` is available on `validate` to opt out of the schema/model
`$id` check; default is to error on mismatch.

That is the entire Phase 0 CLI.

## Worked example: widget record (Profile A)

End-to-end flow.

### Pydantic source

```python
# example_app/schemas/widget_record.py

from datetime import date
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator
from softschema import SField


class Outcome(StrEnum):
    above = "above"
    below = "below"
    on_plan = "on_plan"
    mixed = "mixed"
    none_ = "none"
    n_a = "n_a"


class Direction(StrEnum):
    up = "up"
    down = "down"
    mixed = "mixed"
    flat = "flat"


class EvidenceSnippet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_date: date = SField(
        description="Source publication date. Must be on or before due_date.",
        group="qualitative",
        owner="agent",
        tier="hard_fact",
    )
    source_type: Literal["report", "interview", "news", "dataset", "other"] = SField(
        description="Source category for the snippet.",
        group="qualitative",
        owner="agent",
        tier="constrained",
    )
    observation: str = SField(
        description="One-sentence observation grounded in the source.",
        group="qualitative",
        owner="agent",
        tier="narrative",
        min_length=1,
    )


class Qualitative(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_summary: str = SField(description="...", group="qualitative", min_length=1)
    observed_summary: str = SField(description="...", group="qualitative", min_length=1)
    counterfactual: str = SField(description="...", group="qualitative", min_length=1)
    evidence_snippets: list[EvidenceSnippet] = SField(
        description="Pre-event evidence with source dates and observations.",
        group="qualitative",
        min_length=1,
    )


class WidgetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_id: str = SField(description="Record identifier.", group="identity", tier="hard_fact")
    period: str = SField(description="YYYY-QN.", group="identity", tier="hard_fact")
    due_date: date = SField(description="...", group="identity", tier="hard_fact")
    outcome: Outcome = SField(description="...", group="outcomes")
    direction: Direction = SField(description="...", group="outcomes")
    delta_pct: float = SField(description="...", group="outcomes")
    qualitative: Qualitative = SField(description="...", group="qualitative")

    @model_validator(mode="after")
    def _direction_matches_delta(self) -> "WidgetRecord":
        if self.direction == Direction.up and self.delta_pct < 0:
            raise ValueError(f"direction=up but delta_pct={self.delta_pct}")
        if self.direction == Direction.down and self.delta_pct > 0:
            raise ValueError(f"direction=down but delta_pct={self.delta_pct}")
        return self

    @model_validator(mode="after")
    def _evidence_dates_before_due_date(self) -> "WidgetRecord":
        # The EvidenceSnippet description says "Must be on or before due_date,"
        # but the snippet model alone cannot see the parent due_date; it has to
        # live on the parent. This is the canonical shape of a cross-field invariant
        # that JSON Schema can't express, which is why Pydantic remains canonical.
        for i, snippet in enumerate(self.qualitative.evidence_snippets):
            if snippet.source_date > self.due_date:
                raise ValueError(
                    f"qualitative.evidence_snippets[{i}].source_date="
                    f"{snippet.source_date} is after due_date={self.due_date}"
                )
        return self


class WidgetRecordEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record: WidgetRecord
```

### Compiled JSON Schema sidecar

`softschema compile example_app.schemas.widget_record:WidgetRecordEnvelope --out schemas/widget-record.v2.schema.yaml`
emits the YAML shown in §The JSON Schema sidecar.

### Document instance (new shape)

```markdown
---
softschema:
  spec: "0.1"
  schema:
    ref: ../../../../schemas/widget-record.v2.schema.yaml
  values:
    location: frontmatter
    pointer: /values

values:
  record:
    record_id: WID-001
    period: 2025-Q2
    due_date: 2025-05-01
    outcome: on_plan
    direction: up
    delta_pct: 4.20
    qualitative:
      expected_summary: On-plan baseline result, neutral outlook.
      observed_summary: Operations efficiency expansion.
      counterfactual: Without efficiency gains, the result would be on plan.
      evidence_snippets:
        - source_date: 2025-04-29
          source_type: interview
          observation: Team reported steady throughput improvements.
---
# WID-001 — 2025-Q2 Record

## Why The Result Came In Where It Did

The Q2 outcome landed broadly on plan but a key operations segment delivered
both throughput growth and efficiency gains that downstream consumers priced
as the dominant story.
```

### Document instance (legacy compatibility)

Existing legacy records keep their current shape (no `softschema:` block, `record:` at
frontmatter root). The host pipeline configures the resolver as `frontmatter_root` with
`exclude_keys: ["softschema"]`. Validation runs unchanged.

### Generated section in a runbook

```markdown
## Controlled vocabularies

<!-- softschema:generated kind="enum_table" schema="urn:example.docs:WidgetRecord:v2" view="all_enums" sha256="..." -->
| Field | Allowed values |
| --- | --- |
| outcome | above, below, on_plan, mixed, none, n_a |
| direction | up, down, mixed, flat |
| evidence_snippets[].source_type | report, interview, news, dataset, other |
<!-- /softschema:generated -->
```

CI runs `softschema generate-sections --check` and fails if the table has drifted from
the schema.

## The YAML subset

A conservative subset for authored frontmatter values, locked at Phase 0.

### Allowed

- mappings with string keys
- sequences
- strings (single-line, double-quoted, single-quoted, plain, or block scalars)
- numbers (integer, float)
- booleans `true` / `false`
- null (`null`, `~`, or empty)
- ISO 8601 date and date-time strings (parsed as strings, normalized at the schema
  layer)
- block scalars (`|`, `>`)

### Forbidden

- anchors (`&foo`) and aliases (`*foo`)
- custom tags (`!foo`)
- duplicate keys in a mapping
- implicit YAML 1.1 booleans (`yes`/`no`/`on`/`off`/`y`/`n`)
- non-string mapping keys

### Phase 0 acceptance test

The subset is enforced by a test, not just prose.
The Phase 0 deliverable includes `tests/test_yaml_subset.py` covering:

```text
reject duplicate keys
reject anchors and aliases
reject custom tags
reject yes/no/on/off implicit booleans
reject non-string mapping keys
parse ISO dates as strings (no native parser-coerced date objects)
```

Without the test, the “safe YAML subset” is aspirational and drifts as soon as a clever
document slips past review.

**Comment preservation is not a Phase 0 requirement.** Phase 0 does not rewrite
frontmatter values, so comment-preserving round-trip is not load-bearing yet.
It becomes required only when patches or in-place normalization land (Appendix A.4).

Value canonicalization (sorted keys, deterministic float formatting for instance values)
is also deferred. It becomes load-bearing only when a materialized canonical sidecar
exists. The schema-side canonical hashing rule, however, is Phase 0; see §Schema hashing
in The JSON Schema sidecar.

## Extension points (reserved)

Each is named, scoped, and has an “earned by” condition.
None are Phase 0 work.
This section is the catalog; full design sketches for each, drawn from V5/v6 and the
GPT-5 Pro v6 review, live in [Appendix A](#appendix-a-extension-point-design-sketches).

### Manifest sidecar

V5/v6’s `schemas/<name>.manifest.yaml` listing cross-field invariants by Pydantic method
name. Earned by: a language-neutral consumer that needs to enforce more than the small
`aggregate` DSL covers, OR a schema registry that needs registry metadata, OR migration
maps for v2→v3 schema upgrades.
Until then, optional root `x-softschema` metadata in the schema YAML is sufficient.

### Issue dataclass with repair classes

V5/v6’s rich `Issue` model with `severity`, `repair_class`, `before`, `proposed`,
`confidence`, `patch`, and `source_span`. Earned by: a patch protocol or repair workflow
that consumes the richer fields.
Phase 0 uses Pydantic’s `ValidationError` directly.

### Patch protocol and fill loop

V5’s `set`/`replace`/`append`/`insert`/`remove`/`test` operations addressed by JSON
Pointer or stable field ID, plus the `inspect` API for agent-driven incremental fill.
Earned by: an artifact whose authoring is naturally multi-pass with intermediate
validation. Mining records and predictions are filled in one pass today.

### Mirrors / runtime-rendered fields

V5’s `role="mirror"` for body sections regenerated from canonical values.
Distinct from generated sections (schema-derived).
Earned by: an artifact (e.g. a prediction record’s scenario table) that meaningfully
benefits from inline value display kept in sync with frontmatter.
The marker namespace already accommodates this (`schema.*` versus `value.*` kind
prefixes).

### Materialization sidecar

V5’s `<doc>.values.yaml` with `source.sha256` integrity check.
Earned by: a downstream consumer that benefits from a hash-linked canonical cache.
Today the frontmatter is canonical, the parse is cheap, and consumers re-parse the
source.

### YAML canonicalization

Sorted keys, deterministic float formatting, comment stripping.
Load-bearing only when there is a materialized canonical sidecar to hash.
Lands with materialization.

### Stable-IDs for relational data

Map shapes for KB documents with cross-document references.
Earned by: a concrete relational artifact (e.g., knowledge-base candidates with
primary/related entity fan-out) that demands the design.

### Provider structured-output adapter

`softschema.export_provider_schema(bundle, provider="anthropic"|"openai"|"vertex")` to
down-convert the schema for provider-side validation.
Earned by: a production path through one of those provider schemas where structural
enforcement at the model boundary is worth the maintenance cost.

### Schema versioning migration tooling

`softschema migrate ... --from ... --to ... --map ...`. Earned by: the first v2 → v3
migration. The interface shape is reserved; tooling waits.

### Language-neutral invariant DSL

A richer DSL beyond the few `aggregate` cases (sum, count, all-equal, exists).
Earned by: a cross-language consumer that needs to enforce more than `aggregate` covers.

### Body-form runtime integration

When a body-form runtime (any body-form runtime) arrives in the codebase along with a
real form-shaped artifact, integration is one line per call site:
`runtime.export_values(path)` produces a dict,
`softschema.validate_values(values, model_cls)` validates it.
No softschema-side feature work; no shared code.
v7 documents this only as a design fact, not a planned phase.

## Implementation arc

### Phase 0: contract + validate + generate

```text
softschema/
  __init__.py
  compile.py        # Pydantic → JSON Schema YAML sidecar; canonical-JSON hashing
  validate.py       # validate_values (non-raising) + model_validate_strict + ValueResolver
  schema_view.py    # SchemaView: shared schema reader for all consumers
  generate.py       # <!-- softschema:generated --> regen + --check
  resolve.py        # schema reference resolution (path, URN, softschema.yaml registry)
  yaml_subset.py    # parser with forbidden-construct enforcement
  cli.py            # compile, validate, validate-values, generate-sections, schema-info

tests/
  test_yaml_subset.py   # acceptance test for the YAML subset
  test_schema_view.py   # tests for the shared schema reader
  test_softschema_*.py  # unit tests for compile, validate, generate
```

### Phase 0 definition of done

Phase 0 is done when **all** of the following are true:

1. A Pydantic `WidgetRecordEnvelope` (or any equivalent model) compiles to deterministic
   JSON Schema YAML with `x-softschema` annotations preserved verbatim.
2. The committed sidecar has a canonical-JSON SHA-256 that is stable across YAML
   formatting choices (round-trip-safe).
3. `softschema compile --check` fails on schema drift.
4. `softschema validate` can validate an existing legacy document through the
   `frontmatter_root` resolver.
5. `softschema validate` can validate a new `values_key` document with a `softschema:`
   block.
6. `softschema validate` reports `structural` and `semantic` independently, and the
   schema/model mismatch check fires when `$id`s disagree.
7. `softschema validate-values` can validate a pre-extracted YAML dict, with `--pointer`
   to address a wrapped file.
8. `softschema generate-sections --check` fails when a generated enum table in a
   document is stale relative to the schema.
9. A downstream consumer (e.g., a QA rule or a prompt builder) reads enum values and
   field metadata via `SchemaView` rather than from a local constant table.
10. YAML subset tests reject the forbidden constructs listed in §The YAML subset.

Phase 0 explicitly does **not** include: body-form parsing, patches, inspect,
materialization, mirrors, repair-class issues, manifest sidecar emission, provider
adapters, value canonicalization, or comment-preserving round-trip.

### Phase 1+: extension points

Each reserved extension point in §Extension points is its own phase, gated on a concrete
consumer.

## Risks

### Risk 1: softschema becomes too Pydantic-specific

v7 mostly handles this by saying Pydantic is source of truth in Python projects, while
other schema sources are possible.
The publicly-reusable concept is *schema bundle first, Pydantic compiler for Python
users*, not *Pydantic everywhere*.

### Risk 2: generated sections become ad hoc renderers

Each Phase 0 `kind` (`enum_table`, `field_list`, `vocab`) needs a defined input set and
deterministic output, anchored by the section attributes (`view`, `include_groups`,
`format`, `sort`) and views defined in root `x-softschema.views`. Without that
discipline, generated sections become custom scripts with a shared marker syntax.
The shared `SchemaView` reader is what keeps all kinds going through one logic path.

### Risk 3: structural-only validation is mistaken for full validation

CLI output makes the distinction explicit:

```yaml
validation:
  structural:
    ok: true
    engine: json_schema
  semantic:
    ok: skipped
    reason: no_pydantic_model
```

Consumers that see `structural.ok: true` without `semantic.ok: true` are warned that
cross-field invariants did not run.

### Risk 4: legacy compatibility leaks into the clean format

Legacy widget records (no `softschema:` block, `record:` at frontmatter root) work via
the `frontmatter_root` resolver mode.
That mode is a compatibility seam, not the public format.
New templates require the `softschema:` block and the `values:` shape.

### Risk 5: namespace collisions on `<!-- generated -->`

Mitigated by the `softschema:` namespace on every marker.
Generic `<!-- generated -->` is not a valid softschema marker.

## Open questions

1. **Should new templates also forbid the legacy resolver mode?** v8 treats
   `frontmatter_root` as a compatibility seam.
   Strawman: yes, new templates must use `values_key`. The CLI rejects new templates
   that lack a `softschema:` block.
2. **Generated-section regeneration: edit-time or CI-only?** v8 says CI `--check` fails
   on drift; rerunning the regen command is manual.
   Alternative: a pre-commit hook regenerates automatically.
   Strawman: CI-only initially; pre-commit hook lands if drift complaints accumulate.
3. **What does Profile A do when the schema requires a field absent from frontmatter?**
   Pydantic raises `ValidationError`. No incremental-fill repair workflow in Phase 0. If
   multi-pass fill becomes necessary, the patch protocol earns its keep.
4. **Should `schema-info <schema.yaml>` accept a `--view` flag for previewing generated
   sections?** Useful for debugging.
   Strawman: yes, it is a small addition and helps when a generated section emits
   unexpected content.
5. **Should `softschema` ever split into separate distributions (core / pydantic /
   generate)?** Phase 0 ships as one package.
   Splitting is a future refactor only if the package grows non-Pydantic schema sources
   or the generate-sections code outgrows the core.

## Appendix A: Extension point design sketches

The Phase 0 surface above is intentionally minimal.
This appendix preserves the design content for each reserved extension point so this
document stands alone.
None of this is built today; each section ends with the “earned by” condition that would
unlock it.

### A.1 Body-form runtime integration

When a body-form runtime arrives (a Markdown-form library that captures values inside
the body rather than in frontmatter), the integration point is the `validate_values`
call. The runtime parses the body, exports a values dict, and softschema validates.
There is no shared code; the only requirement is that the runtime emits a values dict
whose shape matches the schema.

**Dependency direction.** A body-form runtime should depend on the softschema
**schema-bundle convention** (a JSON Schema sidecar with `x-softschema` annotations and
optional URN resolution), *not* on the Python `softschema` package.
A body-form implementation can consume JSON Schema plus `x-softschema` metadata, export
values, and leave Pydantic semantic validation to the host.

This way:

- softschema = schema bundle + validation + generated schema sections (Python).
- Body-form runtime = body-side authoring + patch/edit/export (language-agnostic).
- Bridge = exported values validated by softschema or by the host’s Pydantic models.

softschema does not depend on a body-form parser.
The relationship is asymmetric: a body-form runtime optionally consumes softschema’s
bundle convention; softschema remains usable with no body-form runtime involvement at
all.

**Bridge sketch (illustrative):**

```python
import body_form_runtime as bfr
from example_app.schemas.checklist import ChecklistEnvelope
import softschema

values = bfr.export_values("checklist.form.md")
softschema.validate_values(values, ChecklistEnvelope)
```

```bash
body-form export checklist.form.md --values checklist.values.yaml
softschema validate-values checklist.values.yaml \
  --model example_app.schemas.checklist:ChecklistEnvelope
```

**Earned by:** a body-form-runtime dependency arriving along with a real form-shaped
artifact. Until both exist, no bridge ships.

### A.2 Manifest sidecar

V5/v6’s `schemas/<name>.manifest.yaml` parallel to the JSON Schema sidecar.
Carries cross-field invariants the JSON Schema can’t express, plus generation metadata:

```yaml
$id: urn:example.docs:WidgetRecord:v2
schema_ref: ./widget-record.v2.schema.yaml
schema_sha256: "a3f7b2..."
generated_from: example_app.schemas.widget_record:WidgetRecordEnvelope
language_neutral: false
runtime: python

invariants:
  - id: direction_matches_move
    kind: pydantic_model_validator
    model: example_app.schemas.widget_record:WidgetRecordEnvelope
    method: _direction_matches_move
    paths: [/record/direction, /record/delta_pct]
    severity: error

  - id: scenario_probs_sum_100
    kind: aggregate
    op: sum_between
    paths: [/scenarios/*/probability_pct]
    target: 100
    tolerance: 0.5
    severity: error

lifecycle_modes:
  - id: lenient
    description: Partial fill; missing required fields surface as warning issues.
  - id: strict
    description: Complete fill; missing required fields are blocker issues.
```

Three invariant `kind`s:

| `kind` | Resolved as |
| --- | --- |
| `pydantic_model_validator` | A `@model_validator` on the named Pydantic model (Python-only) |
| `external_function` | A module-level callable: `function: pkg.mod:fn` (Python-only) |
| `aggregate` | A small built-in language-neutral DSL: sum, count, all-equal, exists |

**Earned by:** any of (a) a language-neutral consumer that needs to enforce more than
the `aggregate` DSL covers; (b) a schema registry that needs registry metadata; (c)
migration maps for v2→v3 schema upgrades; (d) a generated-section preset library too
large to inline in `x-softschema`. Until then, optional root `x-softschema` metadata in
the schema YAML is sufficient.

### A.3 Issue dataclass with repair classes

V5/v6’s rich error model, intended to bridge validators, agents, QA, repair prompts, and
humans:

```python
class Issue(BaseModel):
    path: str                     # JSON Pointer: "/record/delta_pct"
    field_id: str | None = None   # binding id if known
    code: str                     # "enum_alias_ambiguous", "missing_required", ...
    message: str                  # human-readable
    severity: Literal["blocker", "error", "warning", "info"]
    repair_class: Literal["auto", "proposed", "warning", "unresolved", "blocker"]

    before: Any | None = None
    proposed: Any | None = None
    confidence: Literal["exact", "high", "medium", "low"] | None = None
    reason: str | None = None

    source_span: SourceSpan | None = None
    patch: list[PatchOp] | None = None
    validator: str | None = None
```

Five repair classes:

| Class | Behavior | Example |
| --- | --- | --- |
| `auto` | Rewrite safely and report | `"15.5%"` → `15.5`; trim enum whitespace |
| `proposed` | Suggest, do not rewrite by default | `"not applicable"` → `n_a` vs `none` |
| `warning` | Accept, canonicalize on dump | YAML date object accepted, normalized to `YYYY-MM-DD` |
| `unresolved` | Agent must edit | invalid enum with no exact alias |
| `blocker` | Cannot continue | missing frontmatter; schema ref unresolved |

`severity` is “how bad”; `repair_class` is “what happens next”.
A single issue carries both.

**Earned by:** a patch protocol or repair workflow that consumes the richer fields
(proposed values, confidence levels, source spans for editor integrations).
Phase 0 uses Pydantic’s `ValidationError` directly.

### A.4 Patch protocol and fill loop

Two-phase patch model: structural preflight (atomic; reject whole batch on failure)
followed by semantic post-apply validation (mode-dependent).

**Patch operations** (compile to RFC 6902 JSON Patch internally):

```yaml
- op: set                    # synonym for replace; creates if missing
  path: /record/outcome
  value: n_a

- op: replace                # RFC 6902
  path: /record/outcome
  value: n_a

- op: append                 # array tail
  path: /record/qualitative/evidence_snippets
  value: {source_date: 2025-04-29, source_type: transcript, observation: "..."}

- op: insert                 # array index
  path: /record/qualitative/evidence_snippets/0
  value: {...}

- op: remove
  path: /record/qualitative/evidence_snippets/2

- op: test                   # precondition; batch fails if value differs
  path: /record/record_id
  value: WID-001
```

Patches address by JSON Pointer or by stable field ID (body-form-compatible).
The runtime canonicalizes both forms internally.

**Patch result statuses:**

| Status | Meaning |
| --- | --- |
| `success` | Both phases passed; document changed; no issues |
| `applied_with_issues` | Structural phase passed; semantic issues in lenient mode; document changed |
| `rejected` | Structural failure, or semantic failure in strict mode; document unchanged |

**Fill loop** (`inspect` API): the agent never sees the full schema in its context; it
sees a compact fill state: progress counts, next fields with their constraints and
instructions, and unresolved issues.
The agent builds a patch batch, applies it, repeats until
`progress.filled_required == total_required`.

**Earned by:** an artifact whose authoring is naturally multi-pass with intermediate
validation (e.g., an agent that fills 60+ fields across multiple turns).
Mining records and predictions are filled in one pass today.

### A.5 Mirrors / runtime-rendered fields

Body sections regenerated from canonical values, distinct from generated sections (which
are schema-derived, not value-derived).

Single-value mirror:

```markdown
<!-- softschema:generated kind="value.scalar" path="/record/outcome" -->
**Outcome:** n_a
<!-- /softschema:generated -->
```

Multi-value mirror via Jinja template:

```markdown
<!-- softschema:generated kind="value.template" template="price_table" -->
| Metric | First Window | Scored Close |
| --- | --- | --- |
| Direction | up | up |
| Move | 4.2% | 5.8% |
<!-- /softschema:generated -->
```

The `value.*` kind prefix distinguishes mirrors from `schema.*` generated sections.
Patches that target a mirror’s body content are rejected; the agent patches the
underlying value path and the mirror regenerates.

**Earned by:** an artifact (e.g., a prediction record’s scenario probability table, a
confidence record’s price-window summary) that meaningfully benefits from inline value
display kept in sync with frontmatter.

### A.6 Materialization sidecar

V5’s `<doc>.values.yaml` with `source.sha256` integrity check, plus `<doc>.issues.json`
and `<doc>.fill_log.jsonl`:

```yaml
softschema:
  spec: softschema/0.1
  schema:
    ref: ../../schemas/widget-record.v2.schema.yaml
  source:
    file: record.md
    sha256: "f9c2a1..."
  generated_at: 2026-04-27T14:32:11Z

values:
  record:
    record_id: WID-001
    period: 2025-Q2
    ...
```

Downstream consumers (postprocess, QA, eval judge, dashboards) read the sidecar, verify
`source.sha256` matches the current `record.md` hash, and re-parse the source on
mismatch. The sidecar is a verified cache, not a second source of truth.

**Earned by:** a downstream consumer that benefits from a hash-linked canonical cache.
Today the frontmatter is canonical, the parse is cheap, and consumers re-parse the
source.

### A.7 YAML canonicalization

Lands with materialization.
Specific rules:

- UTF-8 encoding
- LF line endings
- sorted keys (lexicographic) at every nesting level
- block style at the top level; flow style only for empty/leaf containers
- deterministic float formatting (round-trip-safe; no trailing zeros except for
  integer-disambiguation)
- ISO date and date-time strings (no native parser-coerced dates in the hash input)
- comments stripped (canonicalization never preserves comments)

This canonicalization is also used for the schema bundle’s `schema_sha256` (build time)
so consumers can detect that the sidecar matches the manifest they’re trusting.

**Earned by:** materialization.
Without a hash-linked sidecar, there’s nothing to canonicalize for.

### A.8 Stable-IDs for relational data

KB-document shape: instead of index-addressed arrays for durable entities, use mappings
keyed by stable IDs:

```yaml
values:
  entities:
    ENT-001:
      kind: primary
      coverage: full
    ENT-002:
      kind: primary
      coverage: full
  cross_references:
    ENT-001→ENT-002:
      relationship: depends_on
      strength: medium
```

Stable IDs survive document reorganization; index-addressed arrays don’t.

**Earned by:** a concrete relational artifact (e.g., knowledge-base entries with
primary/related entity fan-out, where a
`<PRIMARY>/related/<RELATED>/<RELATED>-<PERIOD>.md` layout has multi-record cardinality
per primary).

### A.9 Provider structured-output adapter

```python
softschema.export_provider_schema(
    schema_bundle,
    provider="anthropic" | "openai" | "vertex",
) -> dict
```

Down-converts the JSON Schema sidecar into each provider’s supported subset.
Constraints unsupported by the provider become local-only validation; the runtime
re-validates against the original sidecar after the response.

**Three use modes:**

1. Generate initial frontmatter values from a structured-output response, then apply as
   a Profile A `values:` block.
2. Generate patch batches from a structured-output response, then apply via the patch
   protocol.
3. Validate-only: provider validates shape; runtime still runs Pydantic semantic
   validators afterward.

**Earned by:** a production path through one of those provider schemas where structural
enforcement at the model boundary is worth the maintenance cost.
claude-code-cli is excluded from this until adapter support lands; Vertex MaaS and
OpenAI are immediate targets when the time comes.

### A.10 Schema versioning migration tooling

V5’s reserved interface:

```yaml
# schemas/widget-record.v2-to-v3.migration.yaml

migration:
  from: urn:example.docs:WidgetRecord:v2
  to: urn:example.docs:WidgetRecord:v3
  map:
    - op: rename
      from: /record/old_field_name
      to: /record/new_field_name
    - op: set_default
      path: /record/new_required_field
      value: null
    - op: enum_remap
      path: /record/outcome
      mapping:
        "not applicable": n_a
    - op: drop
      path: /record/deprecated_field
    - op: derive
      path: /record/computed_field
      from: /record/source_field
      transform: pkg.mod:compute_field  # Python-only
```

CLI:

```bash
softschema migrate runs/.../record.md \
  --from schemas/widget-record.v2.schema.yaml \
  --to schemas/widget-record.v3.schema.yaml \
  --map schemas/widget-record.v2-to-v3.migration.yaml \
  --write
```

Produces a migrated `record.md`, a `record.migration_log.jsonl`, and a strict validate
run against the target schema.

**Earned by:** the first v2 → v3 migration.
Until then, the interface shape is reserved so schema authors plan v2→v3 changes against
a known upgrade story.

### A.11 Language-neutral invariant DSL

Beyond the small `aggregate` ops (sum, count, all-equal, exists) the manifest already
supports. Candidate richer ops: range bounds, conditional invariants ("if A is set, B
must be set"), regex assertions across multiple fields, set-membership operations, etc.

**Earned by:** a cross-language consumer that needs to enforce invariants beyond what
`aggregate` covers. Until then, Python-only `@model_validator`s carry the load.

## References

- [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/schema) — the structural
  schema dialect used by the sidecar.
- [Pydantic v2 JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/) —
  the `json_schema_extra` mechanism that carries `x-softschema` annotations.
- [Pydantic v2 errors](https://docs.pydantic.dev/latest/errors/errors/) — the structured
  `ValidationError` model used directly in Phase 0.
- [frontmatter-format](https://github.com/jlevy/frontmatter-format) — the
  YAML-frontmatter library used for parsing Profile A documents.

<!-- This document follows std-doc-guidelines.md.
Review guidelines before editing.
-->
