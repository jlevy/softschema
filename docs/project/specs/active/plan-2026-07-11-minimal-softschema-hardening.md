---
title: Minimal Softschema Hardening
description: Focused hardening and test simplification from the working main branch
author: Codex, with maintainer direction from Joshua Levy
---
# Feature: Minimal Softschema Hardening

**Date:** 2026-07-11 (last updated 2026-07-11)

**Author:** Codex, with maintainer direction from Joshua Levy

**Status:** Draft

## Overview

Harden the existing Python and TypeScript implementations without replacing their
working architecture.
Preserve the public behavior on `main`, correct only reproduced failures or explicit
trust-boundary gaps, and simplify the test suite around a small set of shared behavioral
contracts.

The work begins from `main`. The earlier hardening branch is evidence about possible
edge cases, not an implementation base.
Code, tests, infrastructure, and abstractions from that branch must earn inclusion
independently against this plan.

The intended result remains a small paired library:

- one language-neutral artifact contract
- idiomatic Pydantic and Zod adapters
- a thin CLI over the public library APIs
- exact parity only where the public contract promises parity
- a small, readable test system with one primary owner for each behavior

## Goals

- Preserve all documented public APIs, commands, artifact formats, exit behavior, and
  package surfaces currently shipped from `main`.
- Define the actual trust model before changing security-sensitive behavior.
- Correct confirmed validation, packaging, installation, and release-boundary defects
  with the smallest design that closes each defect.
- Keep network schema retrieval disabled and installed resources package-relative.
- Keep Python and TypeScript behavior aligned through shared YAML vectors and a small
  set of end-to-end CLI goldens.
- Make tests minimal, transparent, fast, and organized by behavioral responsibility.
- Keep the softschema artifact format simple.
  Contract identity remains the sole authored format/version identity; do not add a
  second `format` version field.
- Improve documentation and agent guidance through one authoritative explanation and
  generated mirrors, not hand-maintained copies.
- Retain the existing standard OIDC publishing workflow while applying focused,
  evidence-based supply-chain controls.

## Non-Goals

- Rewriting the library or introducing a new portable runtime.
- Adding batch discovery, recursive globbing, SARIF, hosted conformance services, GitHub
  Pages publication, or a new diagnostics platform.
- Implementing a YAML parser, regular-expression engine, glob engine, JSON serializer,
  transaction manager, or release state machine.
- Defending against a malicious process with the same user identity modifying local
  files concurrently.
- Treating trusted local Pydantic models, Zod schemas, or registered compiled schemas as
  attacker-supplied executable programs.
- Adding crash journals, installer locks, repair modes, or recovery orchestration.
- Testing GitHub Actions YAML line by line or duplicating registry behavior locally.
- Creating a second conformance corpus beside the shared behavior vectors.
- Adding new public functionality merely because the prior hardening branch implemented
  it.
- Increasing coverage percentages by testing implementation details or obvious object
  construction.
- Adding dependencies without a concrete need, release-age review, and lockfile review.

## Background

Current `main` is a working paired implementation with:

- 6,120 tracked lines of Python and TypeScript production source
- 14 Python test files and 17 TypeScript test files
- 3,981 lines of Python and TypeScript unit-test code
- 15 CLI golden scenarios shared where runtime behavior permits
- 174 tracked repository files
- Python, Node, and Bun validation paths plus cross-implementation checks

The abandoned hardening direction changed 403 files and added 74,060 lines.
Its production additions included new regex, YAML value-domain, bounded-file, discovery,
installer, conformance, diagnostics, and release subsystems.
Each subsystem then required unit, parity, conformance, workflow, and adversarial tests.
That feedback loop made the hardening code larger than the library it was intended to
protect.

This plan treats that outcome as a scope-control failure.
Hardening should reduce reachable states and make trust boundaries explicit.
It should not add general-purpose platforms to a small validation library.

## Design Principles

### Preserve the Existing Shape

Keep the current module boundaries unless a reproduced defect cannot be fixed cleanly
inside them. Prefer a small private helper over a new public module.
Prefer existing YAML, JSON Schema, filesystem, and package-manager behavior over local
reimplementations.

The CLI remains a thin adapter over library functions.
Shared behavior belongs in the libraries; CLI code owns argument parsing, presentation,
and exit-code mapping.

### Require Evidence Before Mechanism

A proposed fix enters implementation only when all of these are recorded:

1. A minimal reproduction against current `main`.
2. The documented public contract or trust boundary it violates.
3. A failing behavioral test at the narrowest appropriate layer.
4. The smallest implementation that makes the test pass.
5. A statement of what stronger threat or feature remains out of scope.

A theoretical concern without a reachable failure, public guarantee, or credible trust
boundary is documented as a non-goal rather than implemented.

### Use a Narrow Trust Model

| Input or actor | Trust level | Required protection |
| --- | --- | --- |
| Artifact Markdown and YAML | Untrusted data | Parse without code execution; validate shape and bounded size; return stable errors |
| Document-declared schema path | Untrusted reference | Relative, bounded local resolution; no network retrieval |
| Explicit local schema file | Trusted file, possibly malformed data | Stable parse and validation errors; no implicit remote references |
| Registered Pydantic or Zod model | Trusted local code | Normal language-runtime behavior; no sandbox or custom regex engine |
| Packaged docs and skills | Trusted package resources | Resolve from the installed package, not the consumer working tree |
| Skill installation target | User-authorized local write | Dry run, target containment, unmanaged-file protection, atomic replacement |
| CI pull-request code | Untrusted until reviewed | No registry credentials or publish authority |
| Protected release job | Trusted workflow and reviewed source | OIDC, least privilege, build once, checksum, install smoke |
| Same-user concurrent local process | Out of scope | No descriptor race framework or transaction journal |

### Keep Complexity Proportional

The implementation must satisfy all of these constraints:

- No new general-purpose parser, interpreter, traversal engine, transaction protocol, or
  release protocol.
- No new top-level subsystem without a separate maintainer decision.
- Target no more than 3,000 net new production lines across both implementations.
- Crossing 3,000 lines requires a written design review explaining each remaining
  component. Crossing 5,000 lines fails this plan and requires replanning.
- Prefer deletion or consolidation whenever a fix introduces more states than it
  removes.
- A Python and TypeScript implementation may differ internally when idiomatic library
  behavior can satisfy the same public contract.
- Exact byte parity is required only for documented machine-readable outputs, compiled
  schema identity, and explicit parity fixtures.
  Human diagnostics may be semantically equivalent unless the public spec promises exact
  text.

Line counts are review triggers, not quality targets.
Compact code that hides complexity does not satisfy the plan.

## Design

### Approach

Implement two phases.
The first characterizes the working behavior and reduces the test model to explicit
ownership. The second applies only the hardening fixes that pass the evidence gate, then
updates public explanations and release validation.

Do not cherry-pick implementation commits from the prior hardening branch.
A small test fixture may be adapted after confirming that it exposes a real `main`
defect and is the minimal expression of that behavior.

### Candidate Hardening Set

These are bounded candidates, not permission to reproduce the prior architecture.
Each must pass the evidence gate before implementation.

#### Validation Boundaries

- Prevent implicit remote `$ref` retrieval by configuring the existing JSON Schema
  validators with an explicit local resource policy.
- Normalize malformed compiled-schema input into the existing structured result and CLI
  exit boundaries.
- Validate the portable YAML value subset after parsing with the existing YAML
  libraries. Reject unsupported values; do not replace either parser.
- Apply simple byte and nesting limits at artifact and schema entry points.
  Use one small helper per language and ordinary iterative traversal where needed.
- Make deterministic serialization explicit only for outputs covered by the public
  parity contract.
- Correct canonicalization or `enforced` overlay behavior only where a minimal schema
  proves a semantic change.

#### Installed Resources and Skill Writes

- Resolve bundled docs, examples, and skill content from the installed package root.
- Keep `skill --install` simple: explicit scope, dry-run preview, repository
  containment, refusal to overwrite unmanaged or modified files, and atomic replacement.
- Do not add locking, journaling, repair, rollback protocols, or concurrent-writer
  defenses.

#### Release Boundary

- Preserve the standard protected-tag and OIDC publishing model.
- Build each Python and npm artifact once, checksum it, and smoke-test the exact built
  artifact before publication.
- Pin reviewed actions and keep registry credentials out of pull-request jobs.
- Validate versions and package contents through built-artifact smoke tests.
- Rely on registry immutability, GitHub environment controls, and rerunnable standard
  jobs. Do not implement a registry state machine or custom recovery bundle.

#### Documentation and Agent Surfaces

- Keep the README a short subset of the guide.
- Keep exact format rules only in the spec, public APIs in `docs/api.md`, and runtime
  decisions in the language design docs.
- Keep one authoritative `skills/softschema/SKILL.md`; generate identical agent-specific
  mirrors only where discovery requires a physical copy.
- Keep agent instructions brief and progressively disclose detail through bundled CLI
  docs.
- Verify the portable `AGENTS.md` entry point and the generated Claude/Codex discovery
  locations. Add another agent-specific surface only when its primary documentation
  requires one and it cannot consume an existing portable surface.
- Describe present behavior.
  Put compatibility history only in the migration guide and changelog.

### Artifact and Version Model

The authored artifact has one logical identity:

```yaml
softschema:
  contract: example.movies:MoviePage/v1
```

Do not add `format: "1"` or another independent file-format version.
The contract ID already identifies the payload contract and its version.
Compiled schema binding remains the optional `softschema.schema` field and does not
create another authored format version.

Unknown inert metadata may be preserved when the spec allows it, but it must not trigger
imports, plugins, retrieval, or validation behavior.

### Test Ownership

Every public behavior has one primary test owner:

| Behavior | Primary owner | Secondary check, when justified |
| --- | --- | --- |
| Cross-language pure transformation or validation rule | Shared YAML vector | One adapter integration assertion per runtime |
| Python/Pydantic-specific behavior | Python unit test | None |
| TypeScript/Zod-specific behavior | TypeScript unit test | None |
| Public CLI command, stdout/stderr, and exit code | End-to-end golden scenario | Direct unit test only for an otherwise unreachable error branch |
| Python wheel or npm package contents | One built-package smoke per ecosystem | Installed CLI smoke |
| Python/TypeScript compiled-schema identity | One cross-runtime parity test | Shared vector cases |
| Release authorization and artifact flow | Workflow smoke and platform controls | Minimal static assertion for a security-critical invariant |
| Documentation or skill resource availability | Built-package smoke | One mirror-drift assertion |

A behavior may appear at more than two layers only when the spec records the distinct
failure each layer catches.
Tests that merely repeat the same input and output at another layer must be removed.

### Shared Vectors and Goldens

- Store portable input and expected structured results as readable YAML.
- Use one vector file or a small set grouped by behavior; do not create a separate
  conformance repository or generated JSON corpus.
- Run the same vectors through Python and TypeScript adapters.
- Keep CLI golden scenarios few and end to end.
  Prefer three to five broad journeys, with a small number of additional error scenarios
  only when they expose distinct exit or stream behavior.
- Keep tryscript Markdown for executable console transcripts where it is clearer than a
  new harness. YAML remains authoritative for structured vector data; JSON shown in a
  transcript remains JSON when that is the CLI’s public output.
- Normalize only genuinely unstable values.
  Do not wildcard stable contract IDs, diagnostics, ordering, or exit codes.
- Keep fixtures public, practical, and small.
  Reuse the movie-page example when it expresses the behavior without obscuring it.
- Treat coverage as a regression floor, not a test-generation target.
  Any coverage waiver must identify unreachable or platform-owned code rather than
  adding trivial tests.

### API Changes

No public API addition is planned.

If a confirmed fix requires a public change, stop implementation and amend this spec
with the exact Python and TypeScript signatures, compatibility behavior, and reason the
existing API cannot express the fix.

Internal helpers remain private unless there is a demonstrated host-library use case.

## Backward Compatibility

**Code types, methods, and function signatures:** KEEP DEPRECATED for already published
public symbols; DO NOT MAINTAIN compatibility for private helpers changed during focused
refactoring.

**Library APIs:** KEEP DEPRECATED. Existing Python and TypeScript public APIs on `main`
must continue to work.

**Server APIs:** N/A.

**File formats:** SUPPORT BOTH only where `main` already accepts multiple documented
forms. Preserve current Markdown/frontmatter and pure-YAML behavior.
Do not add a second version field.

**Database schemas:** N/A.

**CLI:** Preserve current commands, flags, machine-readable result shapes, and exit-code
semantics. A diagnostic wording change is compatible when the wording is not documented
as a machine contract and the structured error remains stable.

## Implementation Plan

### Phase 1: Characterize and Simplify

- [ ] Record the `main` baseline: public exports, CLI surface, documented artifact
  forms, test counts, source lines, and current validation commands.
- [ ] Build a behavior inventory that maps each public guarantee to one primary test
  owner.
- [ ] Run the existing Python, TypeScript, Node, Bun, golden, build, and package-smoke
  checks before changing behavior.
- [ ] Reproduce each candidate hardening defect independently against `main`; reject or
  downgrade candidates that do not cross the stated trust model.
- [ ] Consolidate portable cases into shared YAML vectors without introducing a general
  conformance framework.
- [ ] Reduce CLI goldens to the smallest broad scenarios that retain command, output,
  side-effect, and exit coverage.
- [ ] Remove redundant tests only after a coverage map shows the retained owner catches
  the same regression.
- [ ] Record the accepted fix list, rejected findings, and measured complexity budget in
  this spec before Phase 2 implementation.

**Phase gate:** every accepted fix has a reproduction, trust-boundary statement, failing
test, proposed primary owner, and minimal implementation sketch.
The complete unchanged `main` behavior remains covered.

### Phase 2: Apply Focused Fixes and Validate the Release Boundary

- [ ] Implement accepted validation fixes shared-contract-first, using existing parser
  and validator libraries.
- [ ] Port only the required semantics to the second runtime; keep adapters idiomatic.
- [ ] Apply the minimal installed-resource and skill-write fixes.
- [ ] Apply the minimal build-once, checksum, OIDC, and installed-artifact release
  fixes.
- [ ] Update the guide, spec, API reference, design docs, skill, and agent entry points
  without duplicating explanations.
- [ ] Run the full validation matrix and compare source, test, fixture, and workflow
  growth against the Phase 1 baseline.
- [ ] Perform a deletion pass: remove helpers, fixtures, tests, and abstractions that no
  longer have a unique behavioral responsibility.
- [ ] Produce a validation plan that lists each behavior once, its primary test owner,
  and any justified secondary check.
- [ ] Require a final senior review focused on public compatibility, threat-model fit,
  test ownership, and total design complexity.

**Phase gate:** all documented `main` behavior passes; every accepted defect is fixed;
both packages build and install; the exact artifacts pass smoke tests; no prohibited
subsystem exists; and the complexity limits are satisfied.

## Testing Strategy

Use red-green development for each accepted fix.
Start with the primary owner from the test-ownership table, confirm the test fails for
the intended reason on the unchanged implementation, make the smallest code change, and
run the narrow test before the full matrix.

The required full matrix is:

- Python lint, type checks where configured, and `pytest`
- TypeScript lint, typecheck, unit tests, and coverage floor
- shared YAML vectors through both implementations
- concise CLI goldens under Python and the published Node runtime
- Bun validation only for Bun-supported source/runtime behavior not exercised by Node
- direct compiled-schema identity comparison
- Python wheel build and isolated install smoke
- npm package build, `publint`, pack, and isolated Node import/CLI smoke
- release workflow dry run that cannot publish

Test review must answer:

- What distinct regression does this test catch?
- Is another retained test already responsible for that behavior?
- Does the test assert public behavior or an implementation detail?
- Is the fixture readable and smaller than an equivalent test setup?
- Would a refactor that preserves behavior leave the test unchanged?

Do not use the number of tests as a quality measure.
Report behavioral coverage, coverage percentages, suite runtime, and test/fixture lines
together.

## Rollout Plan

Develop from the clean branch created from current `main`. Do not merge or rebase the
prior hardening implementation into it.

Land the implementation only after both phases’ gates pass.
Release Python and TypeScript together under their existing shared package version
policy. Use a patch release when behavior only closes unintended failures; use a minor
release if an accepted fix changes documented accepted input or a public result shape.

Keep the prior hardening PR open only as an evidence source until the replacement work
has captured every accepted finding.
Then close it without merging.

## Success Criteria

- Existing public functionality from `main` is preserved.
- Every behavior has one named primary test owner.
- Shared portable cases are human-readable YAML.
- CLI goldens are small enough to review in full and cover complete user journeys.
- No custom YAML, regex, glob, transaction, conformance-hosting, or release-state engine
  is introduced.
- Production growth remains within the complexity budget.
- Test growth is explained by unique behavioral responsibility, not layer duplication.
- The README, guide, spec, API docs, design docs, agent instructions, and skill do not
  repeat the same explanation.
- Both built packages install and run outside the source checkout.
- Pull-request CI has no publish authority; release publication uses protected OIDC.

## Open Questions

None at plan creation.
The compatibility requirement is to preserve the documented public behavior on `main`.
Any finding that would require changing that decision must pause implementation and
return to the maintainer with a minimal reproduction and alternatives.

## References

- [Softschema Guide](../../../softschema-guide.md)
- [Softschema Spec](../../../softschema-spec.md)
- [Library API](../../../api.md)
- [Development](../../../development.md)
- [Python Package Design](../../../softschema-python-design.md)
- [TypeScript Package Design](../../../softschema-typescript-design.md)
- [Prior Full Engineering Review](../../reviews/review-2026-06-10-softschema-full-eng-review.md)
- [Prior Review Remediation Plan](plan-2026-06-10-softschema-review-remediation.md)
- tbd `general-testing-rules`
- tbd `golden-testing-guidelines`
- tbd `common-doc-guidelines`
- tbd `supply-chain-hardening`

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
