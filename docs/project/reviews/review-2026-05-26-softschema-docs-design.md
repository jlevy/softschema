# Review: Softschema Docs and Design Organization

**Date:** 2026-05-26

**Status:** Review complete

**Reviewer:** Codex

## Summary

The core design is strong: softschema has a clear center of gravity around
human-readable Markdown, authoritative YAML/frontmatter values, contract IDs that name
payloads rather than implementation classes, and validation at boundaries.
The current documentation already repeats those ideas consistently enough that the repo
has a real shape.

The main problem is not missing content.
It is ownership. The docs currently blur four different jobs:

1. explaining the idea,
2. defining the valid artifact format,
3. recording current release decisions and future design rationale,
4. documenting the Python package implementation.

Because those jobs overlap, the same concepts appear in several places with slightly
different levels of authority.
The largest symptom is `docs/softschema-design.md`: the active public-readiness plan
says not to add a standalone language-neutral design doc for now, while that file
declares itself the durable language-neutral design reference.

My recommendation is to remove `docs/softschema-design.md` from the public doc set
before release, move its still-useful rationale into the active plan spec, and make the
guide more operational: playbooks, common use cases, authoring rules, migration recipes,
CI recipes, and examples of how to use the convention and tool.

## What Is Working

- The repository has the right top-level distinction: the concept is language-neutral,
  and the first implementation is Python.
- `softschema.contract` is consistently framed as a payload contract ID, not a Python
  import path.
- The YAML/frontmatter source-of-truth rule is clear and repeated in the right places.
- The movie-page example is public, practical, and concrete enough to carry the docs.
- The Python package is being kept small.
  The current CLI topics are focused on `readme`, `guide`, `spec`, `python-design`,
  workflow docs, examples, skill, and agent instructions.
- The active public-readiness plan already contains the right instinct: keep broad
  product-design notes in the plan until a permanent public design reference is actually
  earned.

## Primary Findings

### 1. The Standalone Design Doc Conflicts With The Plan

`docs/project/specs/done/plan-2026-05-24-softschema-public-readiness.md` says not to add
a standalone language-neutral `docs/softschema-design.md` for now, and says broad
product-design notes should stay in the plan.
`docs/softschema-design.md` says the opposite: it presents itself as the durable design
reference.

That split will confuse both humans and agents.
A reader cannot tell whether the plan or the design doc owns roadmap, rationale, future
TypeScript direction, generated sections, value resolution, and deferred features.

Recommendation: delete `docs/softschema-design.md` after extracting any unique useful
content, or replace it with a short tombstone that points to the guide, spec, Python
design doc, and active plan.
I prefer deletion before public release because the CLI does not expose it as a docs
topic and the active plan already says it should not be there.

### 2. Current-State And Future-State Rules Are Mixed

The guide and spec currently describe the v0.1 artifact shape as one top-level payload
envelope beside `softschema`. The design doc introduces a future `softschema.values`
pointer shape as canonical for new documents.
The plan lists that choice as a pre-release open question.

That is a normative conflict.
The spec should never leave a reader wondering which artifact shape is valid today.

Recommendation: for v0.1, keep the spec aligned with the code and examples: one
top-level payload envelope beside `softschema`, with envelope inference when exactly one
non-`softschema` key exists.
Keep `softschema.values.location / pointer` in the plan as a future design option unless
the implementation and examples are updated before release.

### 3. Roadmap Content Appears In Too Many Places

The active plan, the research v8 document, and `docs/softschema-design.md` all discuss
field-level `x-softschema`, `SchemaView`, generated sections, warning codes, URN schema
references, provider adapters, body-form bridges, patch protocols, mirrors, and
materialization.

Some overlap is useful while designing, but it is too much for release docs.
The public docs should not make future features feel shipped.

Recommendation: keep the roadmap in the active plan.
Keep v8 as research/source material.
Keep public docs focused on present behavior, with only small forward-looking notes
where they prevent a bad choice.

### 4. The Guide Is Still More Concept Reference Than Playbook

`docs/softschema-guide.md` explains the mental model well, but it is not yet the
operational guide the repo needs.
It has adoption steps, host integration, sidecar notes, and documentation-shape
guidance, but not enough scenario-based help.

Recommendation: restructure the guide around common workflows:

- Adopt softschema for an existing Markdown artifact.
- Decide which values belong in YAML.
- Choose inline frontmatter vs a data sidecar.
- Write a contract ID.
- Add Python validation.
- Validate in CI.
- Migrate a non-canonical existing artifact.
- Use softschema with agents.
- Know when to stop and leave prose as prose.

The guide should carry enough rationale to help readers make decisions, but not the full
roadmap or future architecture.

### 5. The Spec Should Be More Normative And Less Explanatory

`docs/softschema-spec.md` is already concise, but it still carries some teaching content
that overlaps with the guide.
That is acceptable in small doses, but the spec should be the authority on exact
artifact rules.

Recommendation: make the spec answer only these questions:

- What files and profiles are in scope?
- What is the frontmatter shape?
- Is `softschema` optional or required in each state?
- What metadata keys are recognized?
- What is a valid contract ID?
- How is the envelope selected?
- What are valid status values?
- What are schema sidecars vs data sidecars?
- What is the source-of-truth order?
- What must a validator reject?
- Which features are explicitly not part of v0.1?

Motivation, adoption strategy, and examples should mostly live outside the spec.

### 6. The README Is Close, But Should Drop “Design” From Its Public Shape

The README is doing the right job: quick orientation, short example, quick commands, and
links. It currently says `docs/` contains “guide, spec, design, and workflow docs”, but
the public docs list does not include `docs/softschema-design.md`.

Recommendation: after removing or tombstoning the design doc, update the README to say
`docs/` contains guide, spec, Python design, and workflow docs.
Keep the README as a short subset of the guide.

### 7. Project-Internal Docs Need A Clearer Boundary

The repo root docs currently mix public docs (`docs/softschema-guide.md`,
`docs/softschema-spec.md`, `docs/softschema-python-design.md`) with internal planning
and research (`docs/project/specs/...`, `docs/research/...`). The new review folder
helps.

Recommendation: use this boundary consistently:

```text
README.md
docs/
  softschema-guide.md          # public operational guide
  softschema-spec.md           # public normative format spec
  softschema-python-design.md  # Python implementer reference
  installation.md              # workflow support
  development.md               # workflow support
  publishing.md                # workflow support
  project/
    specs/
      active/
    reviews/
    research/                  # optional future move from docs/research
examples/
  movie_page/
skills/
  softschema/
```

Moving `docs/research` under `docs/project/research` is optional, but the direction is
right: public docs at `docs/` root, project-internal design history under
`docs/project/`.

## Recommended Final Doc Roles

| Document | Audience | Owns | Should Not Own |
| --- | --- | --- | --- |
| `README.md` | First-time visitors | What softschema is, one compact example, install/try commands, links | Full rationale, roadmap, exhaustive artifact rules |
| `docs/softschema-guide.md` | Users and agents adopting the pattern | Operational playbooks, common use cases, authoring advice, examples, CI/migration recipes | Normative format minutiae, Python internals, release roadmap |
| `docs/softschema-spec.md` | Tool authors and validators | Exact artifact shape, metadata keys, envelope rules, source-of-truth rules, validation expectations | Motivation, playbooks, roadmap |
| `docs/softschema-python-design.md` | Python package maintainers and contributors | Python modules, public API, CLI surface, validation layers, resource bundling, accepted/rejected Python decisions | Language-neutral manifesto, TypeScript roadmap |
| `docs/project/specs/active/...` | Maintainers planning this release | Current design rationale, tradeoffs, roadmap, open questions, implementation phases | User-facing reference material |
| `docs/research/...` or `docs/project/research/...` | Maintainers doing future design work | Long-form exploration and preserved design history | Required reading for ordinary users |
| `examples/movie_page/README.md` | Users copying the example | What files exist, how to validate them, what the example demonstrates | General concept explanation already covered by guide |
| `skills/softschema/SKILL.md` | Agents | Compact operational checklist and command pointers | Long explanations |

## What To Move Out Of `docs/softschema-design.md`

| Current Design Doc Content | Destination |
| --- | --- |
| Motivation and adjacent alternatives | Active plan background/design rationale; optional short “When to use softschema” section in guide |
| Core principles | Plan design principles; short operational restatement in guide |
| Artifact policy, contract IDs, status, envelope inference | Spec if normative today; plan if rationale/future |
| `softschema.values` pointer shape | Plan open question/future design unless implemented before release |
| Structural vs semantic validation | Python design for implementation details; spec for high-level validation expectation |
| Schema sidecar format and root `x-softschema` fields | Python design for current compiler output; spec only if language-neutral and shipped |
| Field-level `x-softschema`, aliases, `SchemaView` | Plan Phase 5 and v8 research until implemented |
| Generated sections | Plan Phase 7 and v8 research until implemented |
| YAML subset | Spec only for rules enforced today; otherwise plan |
| Runtime API and CLI planned commands | Python design for shipped commands; plan for future commands |
| TypeScript section | `packages/typescript/README.md` or plan deferred decisions |
| Capability roadmap | Active plan only |
| Accepted/deferred/rejected alternatives | Active plan, plus Python-specific accepted/rejected items in Python design |

## Proposed Cleanup Sequence

1. Decide the v0.1 artifact shape explicitly.
   My recommendation is to keep the current one-envelope frontmatter shape for v0.1 and
   defer `softschema.values` until a later non-breaking release.
2. Extract unique useful rationale from `docs/softschema-design.md` into the active
   plan. Do not move all of it.
   Preserve only decisions that affect v0.1 or near follow-on work.
3. Delete `docs/softschema-design.md`, or replace it with a short pointer if keeping a
   compatibility breadcrumb matters.
4. Update README wording and docs links so no public entry point advertises a generic
   design doc.
5. Rework `docs/softschema-guide.md` into an operational guide with playbooks and common
   use cases.
6. Tighten `docs/softschema-spec.md` into the normative artifact-format document.
7. Keep `docs/softschema-python-design.md` implementation-focused and remove any broad
   product manifesto language that belongs in the plan.
8. Update `skills/softschema/SKILL.md`, `AGENTS.md`, and CLI docs topics after the docs
   ownership changes.
9. Run consistency checks:

```bash
rg "softschema-design|Softschema Design|durable design reference" .
uv run softschema docs --list
uv run softschema docs --list --json
uv run python devtools/lint.py --check
uv run pytest
```

## Proposed Guide Shape

```text
# Softschema Guide

## What Softschema Is
## When To Use It
## The Basic Artifact Pattern
## Playbook: Adopt An Existing Markdown Artifact
## Playbook: Choose Consumed Values
## Playbook: Add Python Validation
## Playbook: Validate In CI
## Playbook: Use With Agents
## Playbook: Inline Frontmatter vs Data Sidecar
## Playbook: Migrate An Existing Shape
## Common Mistakes
## Relationship To The Python Package
## Further Reading
```

This would make the guide more useful without turning it into the spec or the plan.

## Proposed Spec Shape

```text
# Softschema Spec

## Scope
## Conformance Language
## Artifact Profiles
## Frontmatter Artifact Shape
## Metadata
## Envelope Selection
## Contract IDs
## Status Values
## Source Of Truth
## Schema Sidecars
## Data Sidecars
## Validation Expectations
## Reserved And Out-Of-Scope Features
```

If the project does not want formal RFC-style `MUST` / `SHOULD` language yet, the spec
can still be normative through clear statements.
The important part is that future design possibilities do not appear as current valid
format rules.

## Specific Decisions I Would Make Now

- Remove the standalone language-neutral design doc from the public doc set.
- Treat the active plan as the home for current design rationale and roadmap.
- Treat v8 as research history and source material, not required public reference.
- Keep the v0.1 spec aligned to the current code and example envelope shape.
- Move the guide toward playbooks and common use cases.
- Keep only purposeful duplication:
  - README: one-sentence version.
  - Guide: operational explanation.
  - Spec: exact rule.
  - Python design: implementation consequence.
  - Skill: compressed checklist.

## Residual Risks

- If generated sections are likely to ship immediately after v0.1, there is a temptation
  to document them early.
  Resist that in public docs until the CLI and tests exist.
- If `softschema.values` is adopted before release, the guide, spec, examples, CLI
  inference behavior, and tests should all change together.
  Partial adoption would make the artifact format ambiguous.
- If `docs/research` stays at the docs root, readers may treat it as part of the public
  product documentation.
  Link to it only from project planning docs unless it is promoted.

## Bottom Line

The clean model is:

- README sells the idea quickly.
- Guide teaches how to use it.
- Spec defines what is valid.
- Python design explains the implementation.
- Plan spec records why the current release is shaped this way and what comes next.
- Research preserves deeper history.

That organization matches the user’s instinct: keep the spec, move motivation and design
rationale into the plan spec, and turn the guide into a practical operating manual.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
