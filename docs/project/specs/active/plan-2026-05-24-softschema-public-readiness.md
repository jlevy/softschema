# Feature: Softschema Public Readiness

**Date:** 2026-05-24 (last updated 2026-05-24)

**Author:** Codex

**Status:** Draft

## Overview

Plan the remaining work in the standalone `jlevy/softschema` repo.

This repo has two jobs:

1. Explain the idea of soft schemas: a language-neutral practice for gradually adding
   structure, exactness, and validation to human-readable artifacts.
2. Ship a specific, convenient Python package that demonstrates and implements the
   Markdown/YAML validation slice of that practice.

The concept comes first.
The Python package is the first concrete implementation, but the artifact format and
mental model should be useful to projects written in any language.

## Goals

- Keep the repo concept-first: soft schemas are a mental model and file convention
  before they are a Python package.
- Preserve the two intended products in the softschema repo:
  - the idea and artifact format for soft schemas
  - the concrete Python implementation
- Make the format understandable to humans and coding agents from the README, guide,
  spec, and examples.
- Keep tools optional.
  A project can adopt only the convention, use the Python package, or map the format to
  another implementation.
- Make YAML/frontmatter the authoritative source for consumed values while keeping
  Markdown readable.
- Validate at boundaries where downstream code, QA, review, or aggregation needs
  reliable structure.
- Keep the Python implementation small, direct, and teachable.
- Leave room for a later idiomatic TypeScript/Zod implementation in this repo.
- Track remaining work as beads linked to this spec.

## Non-Goals

- Do not make Python or Pydantic part of the language-neutral concept.
- Do not implement a TypeScript/Zod package in the first release.
- Do not implement a Markdown body parser for structured fields.
- Do not parse tables or prose as authoritative data.
- Do not implement generic data-sidecar loading in the first Python release.
- Do not build process graph reports, workflow orchestration, repair loops, or provider
  structured-output adapters into the core package.
- Do not carry private compatibility shims, legacy schema names, aliases, or migration
  wrappers into the public API.
- Do not keep softschema planning docs in unrelated repositories.

## Background

Soft schemas are useful because automation, exactness, and structure are separate axes.

| Axis | Lower Structure | Higher Structure |
| --- | --- | --- |
| Automation | human-authored notes | agent or harness generated files |
| Exactness | natural-language judgment | deterministic validation or code |
| Structure | prose and conventions | typed fields or pure data |

Traditional software often made these axes look inseparable: code is automated,
structured, and usually exact.
LLM and agent workflows changed that.
A task can now be automated while still having human-like failure modes: ambiguous
instructions, inconsistent output shape, implicit assumptions, and weak composability.

Soft schemas provide a gradual path:

```text
prose
  -> expected sections and vocabulary
  -> YAML/frontmatter values for consumed fields
  -> schema validation at boundaries
  -> pure data or deterministic code when the shape is stable
```

Projects can move on one axis without forcing movement on the others.
A team may automate a prose-heavy workflow with an agent, add validation to only the
consumed fields, or later replace stable transformations with deterministic code.

## Current State

The `extract-softschema` branch already has the first standalone repo shape:

- Concept-first `README.md`.
- `docs/softschema-guide.md` as the durable concept and adoption guide.
- `docs/softschema-spec.md` as the exact language-neutral artifact format.
- `docs/softschema-python-design.md` as the Python package and implementation design.
- `examples/movie_page` with a practical Spirited Away artifact, model, schema, and host
  integration example.
- `packages/python/src/softschema` with validation, registry, schema compile, and CLI
  code.
- `packages/typescript/README.md` as a future TypeScript/Zod placeholder only.
- `skills/softschema/SKILL.md` and bundled CLI docs/skill commands.
- `softschema docs --list --json` for agent-readable docs discovery.
- `softschema validate` requires a validation implementation via `--model`, `--schema`,
  or both.

## Design

### Repository Shape

The repo is organized as a concept and implementation repo:

| Path | Role |
| --- | --- |
| `README.md` | Short first-visitor orientation, core example, and links |
| `docs/softschema-guide.md` | Standalone concept and adoption guide for humans and agents |
| `docs/softschema-spec.md` | Exact language-neutral artifact format |
| `docs/softschema-python-design.md` | Python package and implementation design |
| `examples/movie_page` | Practical public example with readable Markdown and structured YAML |
| `packages/python` | Python implementation and tests |
| `packages/typescript` | Future TypeScript/Zod notes only |
| `skills/softschema` | Agent-facing skill guidance |

For now, do not add a standalone language-neutral `docs/softschema-design.md`. The
durable public docs are the guide and spec.
Keep product and cross-language design detail in this plan until it is clear that a
permanent design reference is worth another top-level docs file.
Keep `docs/softschema-python-design.md` focused on Python package and implementation
decisions.

### Documentation Model

The README should remain a short subset of the guide.
The guide carries the durable mental model and adoption advice.
The spec carries exact artifact rules.
The package design doc carries implementation choices.
This plan carries the current public readiness roadmap and temporary design notes.

Small docs should stay consolidated.
Avoid reintroducing small standalone docs such as `validation.md`, `schema-bundles.md`,
or `examples.md` unless a topic grows large enough to need a separate reference.

### Design Principles

- **Authoritative structure belongs in YAML or data files.** Markdown body prose and
  tables are reader-facing projections.
- **Contracts name payloads, not implementations.** A `softschema.contract` ID can map
  to Pydantic, Zod, JSON Schema, database records, or custom validators.
- **Boundary-driven hardening beats blanket structure.** Add fields and validation
  because something consumes them.
- **Soft authoring can still have strict validation.** “Soft” describes gradual adoption
  and mixed artifacts, not weak enforcement at a boundary.
- **The language-neutral surface must not leak Python.** Python details belong in the
  Python package docs and implementation APIs.
- **Examples should be practical, public, and few.** One complete example is better than
  a gallery of toy files.

### Adjacent Approaches

The space around softschema is crowded with tools that overlap on parts of the problem.
Recording why those tools don't replace softschema keeps the design honest and guides
both adopters and future contributors:

- **Plain JSON Schema in a YAML file.** Works for pure-data artifacts. Fails for
  artifacts that mix narrative prose with structured values, because nothing tells a
  consumer *which* values are authoritative and where they live.
- **Pydantic (or any source schema) alone.** Carries host-language semantics that don't
  travel cross-language. Loses the portable structural subset that other implementations
  could validate.
- **Full-body form parsers** (Markform, custom Markdown body bindings). Powerful, but
  they own a Markdown body parser and a render runtime. Softschema deliberately does
  not. A body-form runtime can sit *above* softschema, export a values dict, and call
  softschema for validation — no shared code required.
- **Provider structured-output adapters.** Useful at the LLM boundary, but they
  validate one provider's subset; softschema validates the full schema after the model
  responds. The two compose; the adapter is not a substitute.
- **Plain Markdown with hand-maintained convention.** The starting state for most
  projects. Softschema is the smallest possible step up: add metadata, add a contract
  ID, validate the values consumers actually read.

When the guide grows into an operational playbook (see Phase 6), the adopter-facing
version of this list can move into a short "When to use softschema" section there.

### Cross-Language Boundary

The public artifact format is Markdown/YAML plus optional JSON Schema sidecars.
That is the portability boundary.

In the Python package, Pydantic models are the source implementation schema.
In a future TypeScript package, Zod schemas should play that role.
JSON Schema carries the portable structural subset between implementations.

Implementation-specific invariants belong in the implementation schema:

- Pydantic validators for Python
- Zod refinements for TypeScript
- hand-written checks for other hosts

The language-neutral docs should say “source model” or “implementation schema” unless
they are specifically discussing the Python package.

### Future TypeScript/Zod Package

Do not implement the TypeScript package in the first release, but avoid closing the
door. A future TypeScript package should live in this repo and be an idiomatic port, not
a Python translation:

- source schemas in Zod
- runtime validation via `safeParse`
- YAML parsing with the `yaml` package
- deterministic serialization options centralized in one helper
- optional JSON Schema export as the portable structural sidecar
- equivalent concepts and result shapes to the Python package
- no Pydantic naming in the language-neutral surface

### Capability Roadmap Beyond v0.1

Most of the v0.1 surface is a **port of an existing internal package** with deliberate
trims: legacy status, alias resolution, value-path bindings, gzip-on-read, and a few
unused profiles were removed because they served private-history shapes, not the public
concept. The names of the classes, enums, and helpers (`SoftschemaBinding`,
`SoftschemaStatus`, `SoftschemaProfile`, `SoftschemaStage`, `SoftschemaMetadata`,
`SoftschemaRegistry`, `SoftschemaWarning`, `parse_softschema_metadata`) match the
internal package so the downstream port is a dependency switch plus targeted feature
removal, not a sweeping rename.

The capabilities below are the genuinely new work.
They come from
[research-2026-05-24-softschema-runtime-design-v8.md](../../research/research-2026-05-24-softschema-runtime-design-v8.md)
and are not present in the internal predecessor; v8 designs them, this plan implements
them. Read v8 first when picking up any item below.

**P0 capabilities — needed for the package to feel complete to a downstream consumer
beyond the movie example.** Land before the first non-trivial external project depends
on the package.

- **Field-level `x-softschema` annotations** (v8 §"The Pydantic contract layer"). A
  small `SField` helper plus compiler support for per-field `tier`, `owner`, `group`,
  and `instruction` annotations carried through to the JSON Schema sidecar.
  Annotations are advisory; they do not change validation.
  They are the substrate that generated sections, agent prompts, and QA tooling consume.
- **`SchemaView` reader** (v8 §"`SchemaView`: shared schema reader"). One generic JSON
  Schema navigator that every downstream consumer (QA, agent prompts, generated
  sections, comparison tooling) goes through.
  Prevents per-consumer re-parsing drift.
- **Stable warning-code scheme.** The package already emits codes like
  `document-softschema-invalid`. Enumerate every code, document them as a public table,
  and add a regression test that holds the table to the emitted codes.

**P1 capabilities — make the package immediately useful for adoption-stage projects.**

- **Generated schema sections** (v8 §"Generated sections"). Markers in Markdown that the
  package regenerates deterministically from a schema.
  Initial kinds: `enum_table`, `field_list`, `vocab`. Reads through `SchemaView`. Needs
  a `--check` mode for CI.
- **Documentation enhancements.** A lifecycle/continuum walkthrough, an
  inline-vs-sidecar doctrine, a migration recipe for projects with non-canonical
  envelopes, and a CI-integration recipe.
  All doc-only; no code.

### Deferred Work

These appear in the design influences below but are explicitly out of scope for v0.1 and
the immediate follow-on releases.
Each will be revisited only when a concrete public use case earns the design cost.

- Alias-repair semantics with controlled-vocabulary single-target and multi-target
  resolution. Useful for agent-generated artifacts with typo tolerance; risky because
  repair can grow into a second validation language if not scoped carefully.
- URN-based schema references with a repo-level `softschema.yaml` registry.
  Useful for cross-repo schema sharing; most projects can stay path-only.
- Patch protocol and multi-pass fill loops for agent-driven incremental authoring.
- Provider structured-output adapters for Anthropic, OpenAI, and Vertex.
- Body-form / Markform runtime bridges that read structured values from rendered
  Markdown forms.
- A language-neutral invariant DSL beyond what JSON Schema already expresses.
- Value mirrors (instance-derived doc sections), distinct from schema-derived generated
  sections.

### Design Influences

The capability roadmap above is informed by a longer-running runtime-design research
thread captured in
[docs/project/research/research-2026-05-24-softschema-runtime-design-v8.md](../../research/research-2026-05-24-softschema-runtime-design-v8.md).
That document describes the full “hard schema, soft authoring” architecture in detail —
including Phase 0 surface, generated-section markers, `SchemaView`, schema reference
resolution, the `softschema:` block policy, the YAML subset, and a catalog of reserved
extension points (manifest sidecars, patch protocol, mirrors, materialization, provider
adapters, body-form bridges, language-neutral invariant DSL).

This public package is deliberately narrower than that research:

- **What v8 says, this package adopts.** The core principles (Pydantic source of truth
  in Python, JSON Schema as portable sidecar, `x-softschema` as annotation-only,
  structural and semantic validation as independent engines, language-neutral artifact
  format) match what v0.1 ships today.
- **What v8 says, this package will adopt.** The P0/P1 capabilities above (field-level
  `x-softschema` metadata, `SchemaView`, stable warning-code prefixes, generated
  sections, lifecycle/sidecar/migration/CI documentation) are the parts of v8 that are
  cheap to extract and broadly useful.
- **What v8 says, this package defers.** The items in the *Deferred Work* section above
  (alias-repair semantics, URN registry, patch protocol, provider adapters, body-form
  bridges, value mirrors, language-neutral invariant DSL) are reserved in v8 too.
  Each is named, scoped, and earned by a concrete consumer; none are first-release work
  here.

Read v8 when designing any of the P0/P1/P2 items above.
Update v8 when this plan’s direction diverges from it; the v8 doc is the durable design
reference, and this plan is the time-bounded execution roadmap.

## Implementation Plan

### Phase 0: Preserve the Plan in the Right Repo

- [x] Create this softschema-owned plan spec.
- [x] Copy the reusable design framing out of the accidental tryscript plan.
- [x] Link implementation beads to this spec.
- [x] Remove accidental softschema planning work from the unrelated tryscript repo after
  this plan is committed and pushed.

### Phase 1: Documentation Review

- [ ] Review `README.md` as the first-visitor entry point.
- [ ] Review `docs/softschema-guide.md` as the durable concept and adoption guide.
- [ ] Review `docs/softschema-spec.md` as the exact artifact format.
- [ ] Review `docs/softschema-python-design.md` as Python package design, not a broad
  product manifesto.
- [ ] Keep this plan as the temporary home for broad product-design notes unless a
  permanent language-neutral `docs/softschema-design.md` becomes clearly useful.
- [ ] Run a consistency pass across `README.md`, `docs/softschema-guide.md`,
  `docs/softschema-spec.md`, `docs/softschema-python-design.md`, `AGENTS.md`,
  `skills/softschema/SKILL.md`, and `examples/movie_page/README.md` to confirm each
  agrees on three points:
  - the practice is language-neutral and the current implementation is Python
  - the YAML/frontmatter payload is authoritative and the Markdown body is reader-facing
  - `softschema.contract` names the payload contract, not the schema of the
    `softschema:` metadata block

### Phase 2: Example Review

- [ ] Verify `examples/movie_page/spirited-away.md` is friendly, readable, and contains
  the same structured information as its YAML payload.
- [ ] Verify the movie example includes title, description, structured domains, readable
  body prose, a table, Rotten Tomatoes critics/audience ratings, and vote/review counts.
- [ ] Verify `examples/movie_page/model.py` remains simple enough to understand by
  reading it directly.
- [ ] Verify the integration test uses the example code rather than duplicating hidden
  demo logic.

### Phase 3: Python Package Review

- [ ] Review public API names with no backward-compatibility constraint.
- [ ] Keep complete binding registration and avoid aliases, legacy statuses, and
  compatibility projections.
- [ ] Verify `softschema validate` reads contract/status/envelope from the artifact by
  default and treats CLI flags as overrides.
- [ ] Verify `softschema validate` requires `--model`, `--schema`, or both.
- [ ] Verify bundled docs and examples are included in wheel and sdist.
- [ ] Verify `frontmatter-format` is documented as the frontmatter/YAML mechanics
  dependency, not a generic data-sidecar runtime.
- [ ] Record CLI topic rename in release notes: `softschema docs design` is now
  `softschema docs python-design`, matching the `docs/softschema-python-design.md`
  filename.

### Phase 4: Release Readiness

- [ ] Run `uv run python devtools/lint.py --check`.
- [ ] Run `uv run pytest`.
- [ ] Run `uv build`.
- [ ] Inspect the built wheel for bundled resources, including the renamed
  `docs/softschema-python-design.md`
  (`unzip -l dist/*.whl | grep softschema-python-design`).
- [ ] Run `softschema docs --list`, `softschema docs --list --json`,
  `softschema docs guide`, and `softschema skill --brief`.
- [ ] Run the movie example validation command from the README.
- [ ] Confirm tbd sync is healthy.

### Phase 5: P0 Capability Implementation

Each item is net-new relative to the ported core.
Designs live in v8; this phase implements them.
Land before the first non-trivial external project depends on the package.

- [ ] **Field-level `x-softschema` annotations** (v8 §"The Pydantic contract layer").
  Add an `SField` helper, surface per-field `tier`/`owner`/`group`/`instruction` through
  `softschema.compile`, document the allowed keys in `docs/softschema-python-design.md`,
  annotate one field in the movie example, and add a round-trip test.
- [ ] **`SchemaView` reader** (v8 §"`SchemaView`: shared schema reader"). New
  `softschema.schema_view` module.
  Match the v8 interface (`iter_fields`, `field`, `enum_values`, `softmeta`,
  `fields_by_group`/`owner`/`tier`). Export from `softschema/__init__.py`. Add tests for
  enum extraction, required-field listing, missing-key handling, and annotation
  retrieval.
- [ ] **Warning-code documentation.** Enumerate every emitted code, publish the table in
  `docs/softschema-python-design.md` as stable public surface, and add a regression test
  that asserts the package only emits documented codes.

### Phase 6: P1 Documentation Enhancements

Doc-only; ships independently of Phase 5 and Phase 7.

- [ ] Lifecycle / continuum walkthrough in `docs/softschema-guide.md`.
- [ ] Inline-vs-sidecar doctrine section in the guide.
- [ ] Migration recipe (legacy envelope → canonical) in the guide, using `ValueResolver`
  modes.
- [ ] CI integration recipe in `docs/development.md` (`softschema compile --check`
  + GitHub Actions snippet + `pre-commit` example).

### Phase 7: P1 Generated Schema Sections

The biggest follow-on feature.
Designed in v8 §"Generated sections" (markers, attributes, views, hash semantics,
allowed kinds, CI integration).
Implementation should follow v8 closely; do not redesign here.

- [ ] Add the marker format to `docs/softschema-spec.md` (kinds `enum_table`,
  `field_list`, `vocab` for Phase 0; see v8 §"Allowed `kind` values (Phase 0)").
- [ ] Add a `softschema.generate` module with one renderer per kind, reading through
  `SchemaView`.
- [ ] Add `softschema generate <file>` and `softschema generate <file> --check` CLI
  subcommands.
- [ ] Add one generated-section marker to `examples/movie_page/README.md` so the example
  exercises the feature end-to-end.
- [ ] Tests: renderer determinism, drift detection, marker round-trip, failure modes.

## Tracking Beads

| Bead | Status | Role |
| --- | --- | --- |
| `ss-avhi` | in progress | Parent epic for the public readiness plan. |
| `ss-h4sp` | closed | Remove accidental softschema planning artifacts from tryscript. |
| `ss-thj8` | open | Review README, guide, spec, and docs structure. |
| `ss-oovv` | open | Review the movie page example and integration tests. |
| `ss-va24` | open | Review Python API, CLI behavior, and bundled resources. |
| `ss-szpe` | open, blocked by docs/example/API review | Run final release readiness validation. |
| `ss-f8in` | closed | Enumerated Phase 1 review targets in this plan. |
| `ss-f3uw` | closed | Trimmed transient tbd sync line from Current State. |
| `ss-1h7p` | closed | Phase 4 verifies bundled docs after rename. |
| `ss-3523` | closed | AGENTS.md now links the python design doc for implementers. |
| `ss-pjqg` | closed | Open Questions split into pre-release vs deferred. |
| `ss-0vrt` | closed | Named `x-softschema` fields in python design doc. |
| `ss-7lf3` | closed | Trimmed tryscript history paragraph from plan Overview. |
| `ss-j6fu` | closed | CLI topic rename `design` → `python-design` noted in Phase 3. |
| `ss-pu9z` | open, P0 | Field-level `x-softschema` annotations through compile. |
| `ss-9zdi` | open, P0 | `SchemaView` shared schema reader. |
| `ss-befh` | open, P0 | Stable warning-code prefix scheme (documented + tested). |
| `ss-0cz4` | open, P1 | Lifecycle / continuum walkthrough in the guide. |
| `ss-ow97` | open, P1 | Inline-vs-sidecar doctrine in the guide. |
| `ss-91vh` | open, P1 | Migration recipe (legacy envelope → canonical). |
| `ss-4e4s` | open, P1 | CI integration recipe in development docs. |
| `ss-bini` | open, P1, epic, blocked by `ss-9zdi` | Generated schema sections (markers + renderer + CLI). |

## Testing Strategy

Plan-only changes:

```bash
git diff --check
tbd doctor
```

Full package validation:

```bash
uv run python devtools/lint.py --check
uv run pytest
uv build
```

Resource validation:

```bash
uv run softschema docs --list
uv run softschema docs --list --json
uv run softschema docs guide
uv run softschema docs spec
uv run softschema docs example-artifact
uv run softschema skill --brief
```

## Rollout Plan

1. Commit and push this plan spec in the softschema repo.
2. Remove accidental softschema planning work from the unrelated tryscript repo.
3. Work through the linked softschema beads.
4. Keep docs changes in the softschema repo only.
5. Publish or tag the standalone package only after docs, examples, CLI resources, and
   tests pass.

## Settled Pre-Release Decisions

These were open in earlier revisions and are now settled. They are recorded here
rather than as code comments so the rationale is visible to the next reader.

- **Standalone `docs/softschema-design.md` is removed for v0.1.** The 2026-05-26
  codex review (`docs/project/reviews/review-2026-05-26-softschema-docs-design.md`)
  flagged a conflict with this plan. The guide, spec,
  `docs/softschema-python-design.md`, the v8 research doc, and this plan are the
  durable docs. A permanent language-neutral design doc can be revisited after the
  first downstream migration if a need actually appears.
- **Public API names keep the `Softschema*` namespace prefix.** Earlier drafts of
  the trading adoption plan sketched shorter names (`SchemaBinding`, `Status`); the
  shipped API uses `SoftschemaBinding`, `SoftschemaRegistry`, `SoftschemaStatus`,
  `SoftschemaProfile`, `SoftschemaStage`, `SoftschemaMetadata`, `SoftschemaWarning`,
  `parse_softschema_metadata`. The namespaced form is preserved so consumer code
  (host `Status`, host `Binding`) doesn't collide on import. The trading repo
  Phase 3 cutover will write `from softschema import SoftschemaBinding`.
- **`softschema.values.location / pointer` is deferred past v0.1.** v8 prescribes
  an explicit `softschema.values: {location: frontmatter, pointer: /values}` block
  instead of inferring the envelope from the first non-`softschema` top-level key.
  The current package infers; the spec documents inference as the v0.1 rule and
  excludes the resolver shape in `Out of Scope for v0.1`. A non-breaking
  `ValueResolver` mode for the explicit form can ship in a later release once an
  artifact actually needs it.

## Open Questions

### Pre-Release Decisions

These should be resolved before tagging the first PyPI release.

- Which downstream repo should be migrated first once the standalone package is ready?
  Default if unresolved: pick the smallest internal consumer to validate the published
  API surface.
- **Warning-code prefix commitment.** Public consumers will need to filter on these
  prefixes. Pick one (`document-*`, `meta-*`, or `softschema-*`) and freeze it before
  v0.1; record the choice in the warning-codes subsection of the python design doc.
  Default if unresolved: `document-*` for document-metadata warnings.

### Deferred Decisions

These can wait until a TypeScript package is actually scheduled.

- Should the future TypeScript package be named `@softschema/core`, `softschema`, or a
  different scoped name?
- Should JSON Schema export be part of the first TypeScript package, or a later optional
  package?
- **Should `softschema` ever split into separate distributions** (core / pydantic /
  generate-sections)? v8 raises this as an open question.
  Phase 0 ships as one package; splitting is a future refactor only if generate-sections
  grows large or non-Pydantic schema sources arrive.

## References

- [Softschema Guide](../../../softschema-guide.md)
- [Softschema Spec](../../../softschema-spec.md)
- [Python Package Design](../../../softschema-python-design.md)
- [Runtime Design v8](../../research/research-2026-05-24-softschema-runtime-design-v8.md)
  — the durable design reference for the full “hard schema, soft authoring”
  architecture. P0/P1/Deferred items in this plan trace back to this document.
- [Movie Page Example](../../../../examples/movie_page/README.md)
- [Future TypeScript Notes](../../../../packages/typescript/README.md)

<!-- This document follows std-doc-guidelines.md.
Review guidelines before editing.
-->
