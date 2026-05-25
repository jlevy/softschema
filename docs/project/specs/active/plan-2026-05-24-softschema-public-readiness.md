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

This plan is also the place to preserve the useful design framing from the accidental
tryscript plan before that unrelated repo is cleaned up.
Do not create or keep softschema planning artifacts in tryscript.

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

The branch and tbd sync state are pushed in `jlevy/softschema`.

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
- [ ] Ensure docs consistently explain that the practice is language-neutral and the
  current implementation is Python.
- [ ] Ensure docs consistently say the YAML/frontmatter payload is authoritative and the
  Markdown body is reader-facing.
- [ ] Ensure docs consistently explain `softschema.contract` as the payload contract,
  not the schema of the `softschema:` metadata block.

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

### Phase 4: Release Readiness

- [ ] Run `uv run python devtools/lint.py --check`.
- [ ] Run `uv run pytest`.
- [ ] Run `uv build`.
- [ ] Inspect the built wheel for bundled resources.
- [ ] Run `softschema docs --list`, `softschema docs --list --json`,
  `softschema docs guide`, and `softschema skill --brief`.
- [ ] Run the movie example validation command from the README.
- [ ] Confirm tbd sync is healthy.

## Tracking Beads

| Bead | Status | Role |
| --- | --- | --- |
| `ss-avhi` | in progress | Parent epic for the public readiness plan. |
| `ss-h4sp` | closed | Remove accidental softschema planning artifacts from tryscript. |
| `ss-thj8` | open | Review README, guide, spec, and docs structure. |
| `ss-oovv` | open | Review the movie page example and integration tests. |
| `ss-va24` | open | Review Python API, CLI behavior, and bundled resources. |
| `ss-szpe` | open, blocked by docs/example/API review | Run final release readiness validation. |

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

## Open Questions

- Should a permanent language-neutral `docs/softschema-design.md` exist later, or are
  the guide, spec, `docs/softschema-python-design.md`, and this plan enough?
- Should the future TypeScript package be named `@softschema/core`, `softschema`, or a
  different scoped name?
- Should JSON Schema export be part of the first TypeScript package, or a later optional
  package?
- Which downstream repo should be migrated first once the standalone package is ready?

## References

- [Softschema Guide](../../../softschema-guide.md)
- [Softschema Spec](../../../softschema-spec.md)
- [Python Package Design](../../../softschema-python-design.md)
- [Movie Page Example](../../../../examples/movie_page/README.md)
- [Future TypeScript Notes](../../../../packages/typescript/README.md)

<!-- This document follows std-doc-guidelines.md.
Review guidelines before editing.
-->
