---
title: Minimal Softschema Hardening
description: Focused hardening and test simplification from the working main branch
author: Codex, with maintainer direction from Joshua Levy
---
# Feature: Minimal Softschema Hardening

**Date:** 2026-07-11 (last updated 2026-07-11)

**Author:** Codex, with maintainer direction from Joshua Levy

**Status:** Approved

**Tracking:** `ss-gwdt` (minimal hardening implementation epic)

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

- Preserve the useful capabilities and user workflows currently shipped from `main`.
  APIs, flags, result shapes, and format details may change where one clean replacement
  is simpler or more correct.
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
- Carrying deprecated aliases, compatibility wrappers, dual result shapes, or parallel
  old and new implementations into the new minor release.

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
| Explicit local schema file | Trusted project configuration, possibly malformed | Stable parse and validation errors; no implicit remote references |
| Registered Pydantic or Zod model | Trusted local code | Normal language-runtime behavior; no sandbox or custom regex engine |
| Packaged docs and skills | Trusted package resources | Resolve from the installed package, not the consumer working tree |
| Skill installation target | User-authorized local write | Dry run, target containment, unmanaged-file protection, atomic replacement |
| CI pull-request code | Untrusted until reviewed | No registry credentials or publish authority |
| Protected release job | Trusted workflow and reviewed source | OIDC, least privilege, build once, checksum, install smoke |
| Same-user concurrent local process | Out of scope | No descriptor race framework or transaction journal |

A document may select a schema only within the trusted project boundary.
The schema is trusted configuration even when the artifact is untrusted data.
Protect against invalid schema syntax, unavailable references, and accidental resource
exhaustion; do not build a sandbox for computationally malicious schemas or models.

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
- Cross-runtime parity means the same structured meaning, error codes, paths, and exit
  classes. Do not require byte-identical pretty JSON where JSON object order and number
  spelling are semantically irrelevant.
- Use a standards-based canonical JSON representation only where bytes are identity,
  such as the compiled-schema digest.
  Do not maintain a general-purpose custom JSON serializer for CLI presentation.

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

The verified starting behavior and one reproduction for each accepted defect are in
[Minimal Hardening Baseline](../../reviews/review-2026-07-11-minimal-hardening-baseline.md).

### Previous PR Bug-Fix Disposition

The previous PR mixed defects present on `main`, product additions, and defects in its
own new infrastructure.
Only the first group is presumptively in scope.
Each accepted item still requires a minimal failing regression against `main` before
implementation.

#### Applicable Defects From `main`

| Defect | Required correction | Primary test owner |
| --- | --- | --- |
| Missing, unreadable, malformed, and invalid-UTF-8 artifacts crossed inconsistent library and CLI boundaries | Distinguish access/input failures from readable-content parse failures in both runtimes. Return stable structured reasons and preserve the `2` versus `1` exit distinction. | Shared artifact-input YAML vectors |
| Python could retrieve unresolved remote JSON Schema references | Use an offline validator registry. Allow only the root schema and explicitly supplied, already-loaded resources. | Shared reference YAML vectors |
| Root, embedded, and explicitly supplied JSON Schema resources were identified and resolved differently by the two validators | Index local `$id`, `$anchor`, and JSON Pointer targets consistently, reject duplicate resource identities, and resolve only within the closed in-memory registry. | Shared local-resource YAML vectors |
| Readable malformed schemas escaped through different exceptions and exit classes | Return one structured `schema_invalid` family with stable reasons for syntax, dialect, reference, regex, and compilation failures. Keep file access and invocation failures as input errors. | Shared schema-failure YAML vectors |
| Python and JavaScript YAML parsers materialized different values | Define one JSON-compatible value domain: string keys, exact safe integers, finite numbers, no timestamps, duplicate keys, merge keys, aliases, custom tags, negative zero, lone surrogates, or unsupported scalar forms. Configure and inspect the existing parsers; do not replace them. | Shared portable-value YAML vectors |
| Artifact and schema reads were unbounded | Check a modest byte limit before reading and enforce depth, node, and scalar limits after parsing. The byte limit bounds parser allocation; incremental parser construction and descriptor race defenses remain out of scope. | One boundary unit per runtime plus shared limit vectors |
| TypeScript `format` assertions differed from Python’s annotation-only behavior | Treat `format` as an annotation in both validators unless a later contract explicitly opts into a named assertion vocabulary. | Shared structural vectors |
| Python and JavaScript regular-expression dialects can disagree | Define and validate a small common pattern syntax before using the native validators. Reject unsupported constructs and bound pattern length. Schemas are trusted, so do not implement a regex VM, DFA cache, or adversarial execution fuel. | Shared pattern YAML vectors |
| Pretty JSON and schema hashes relied on incompatible host ordering and number spelling | Compare CLI JSON structurally. Use an RFC 8785-compatible canonical JSON implementation only for digest preimages, after portable-value validation. | Shared digest vectors and semantic CLI goldens |
| Canonicalization could rewrite annotation data or miss schema-bearing keywords | Traverse only recognized JSON Schema subschema positions, preserve unknown and annotation values verbatim, normalize only documented semantic no-ops, and use one specified ordering for set-like arrays. | Shared canonicalization vectors with before/after validation assertions |
| The `enforced` overlay could reject valid composed schemas | Apply closure only where it is semantics-preserving. Return `enforcement_unsupported` for composition or evaluation shapes that cannot be closed safely without changing meaning. | Shared enforcement vectors |
| Contract IDs were validated inconsistently and were copied into JSON Schema `$id` | Validate contract IDs at every public construction/registry/compiler boundary. Store the logical contract only in `x-softschema.contract`; accept a separate optional absolute schema resource ID for `$id`. | Shared identity vectors plus one compiler parity test |
| Compiler-owned root metadata could be silently merged, replaced, or crash by type | Reserve root `x-softschema` for the compiler and reject model-supplied collisions before writing. Require a contract ID for compilation. | Shared compiler vectors |
| Python and TypeScript field-annotation helpers accepted different invalid `x-softschema` metadata | Validate the retained annotation fields at authoring time with the same nonempty-string, integer, enum, alias, and portable-value rules. Remove annotation fields that have no real consumer instead of preserving unused surface. | Shared annotation compiler vectors |
| Compiler drift checks could equate Python `true` and `1`, accept invalid UTF-8, or compare nonportable values | Parse committed sidecars as strict UTF-8, validate the portable domain, and compare their canonical structured representation. Write exact UTF-8 bytes atomically. | Compiler unit test per runtime and one parity case |
| `SchemaView` discarded `$ref` sibling annotations and oversimplified genuine unions as nullable single values | Preserve allowed `$ref` sibling annotations, report a single type or enum only for an exact nullable-single-value shape, leave genuine unions unresolved, and snapshot mutable input. | Shared SchemaView vectors run by both adapters |
| `SchemaView.contract_id` treated JSON Schema `$id` as a logical contract | Read contract identity only from validated `x-softschema.contract`; expose schema resource identity separately. Do not retain the `$id` fallback in the hard cut. | Shared identity and SchemaView vectors |
| TypeScript document-declared schema containment was lexical and could follow an in-tree symlink outside the project boundary | Resolve the real target before the containment check in both runtimes. Keep same-user path replacement races out of scope. | One filesystem boundary test per runtime |
| The existing TypeScript model loader imported raw path strings, so spaces, URL metacharacters, and Windows paths could resolve incorrectly | Parse `path:export` on the final colon, convert the resolved local path with `pathToFileURL`, and give a clear Node-built-JavaScript versus Bun-TypeScript error. Keep model loading trusted and local. | Focused TypeScript adapter tests |
| Installed CLI resources could be shadowed by a consumer repository | Resolve installed docs, examples, and skills from package resources. Permit live source resources only when the module has the exact source-checkout layout. | Built-package collision smoke per ecosystem |
| `skill --install` overwrote unmanaged or locally modified files and inferred scope too freely | Require explicit project or personal scope, support dry run, constrain targets, refuse unmanaged or modified files, and replace managed files atomically. | One shared behavioral matrix exercised through each CLI |
| Agent bootstrap examples used unpinned zero-install commands while claiming a release-age policy that consumers may not have | Prefer an installed qualifying CLI. Make any zero-install fallback use one centrally generated, exact last-verified package version and a noninteractive invocation. | Skill content assertion and installed-package smoke |
| CI and publication rebuilt or trusted artifacts across an incompletely closed boundary | Pin reviewed actions, install from frozen locks, build wheel/sdist/npm tarball once without publish authority, checksum them, smoke the exact transferred artifacts on supported operating systems, then publish those bytes through protected OIDC jobs. | Workflow dry run plus built-artifact matrix smoke |
| Public docs and agent guidance overstated byte parity, schema trust, bootstrap safety, and agent-target support | Rewrite claims to match the hard-cut semantic parity and trust model; keep exact rules in the spec, APIs in one reference, and agent-specific claims tied to primary documentation or tested discovery. | Link/claim audit plus installed docs smoke |

#### Changes That Do Not Carry Forward

| Previous PR work | Disposition |
| --- | --- |
| Authored `format: "1"`, legacy metadata schemas, and format negotiation | Excluded. The contract is the authored identity; there is no second artifact version. |
| Portable-core package split and compatibility re-exports | Not a bug fix. Refactor only where the accepted fixes make a smaller module boundary; add no compatibility layer. |
| Batch discovery, recursive globbing, JSONL, SARIF, positioned diagnostics, and source maps | Excluded product additions. |
| Standalone conformance runner, publication site, Pages promotion, archive consumer, and evolution registry | Excluded platform additions. Shared YAML vectors are the conformance source. |
| Transactional installer journals, locks, rollback, repair, and bounded inspection of those files | Excluded. They fixed complexity introduced by the transactional installer. |
| Custom regex NFA/DFA, cache limits, aggregate fuel, and later automata fixes | Excluded. Use a restricted common syntax with trusted schemas and native validators. |
| Recursive discovery limits, iterative glob fixes, symlink deduplication, and candidate work budgets | Excluded because discovery and glob systems are excluded. |
| Frozen release driver, registry state machine, recovery bundles, immutable-release retries, checksum parser, and associated descriptor/Windows race fixes | Excluded. Use standard build-once artifacts and rerunnable protected publishing jobs. |
| Conformance-adapter request validation and the boolean-limit review comment | Excluded. The adapter was new, and the reported boolean acceptance was a false positive. |
| Pure-YAML CLI exposure, serializable TypeScript contract descriptors, runtime binding registry, and a larger model-loading product surface | Not bug fixes. Existing pure-YAML and trusted local model-loading capabilities remain; only the concrete TypeScript path-resolution defect above carries forward. Other additions require separate product justification. |
| Test-only fixes for the discarded artifact verifier, npm consumer, Pages publisher, and release recovery tooling | Excluded with their owning systems. |
| Conversion of human-reviewed fixtures from JSON to YAML and removal of duplicate tests | Retain as test-design requirements, not runtime features. |

This table is the coverage checklist for the earlier PR. A newly discovered candidate
must be added here with a disposition before implementation; it must not enter through a
new bead without a spec update.

### Accepted Hardening Set

The applicable defects above define the bounded hardening set.
They do not authorize the previous PR’s architecture.

#### Validation Boundaries

- Prevent implicit remote `$ref` retrieval by configuring the existing JSON Schema
  validators with an explicit local resource policy.
- Normalize malformed compiled-schema input into the existing structured result and CLI
  exit boundaries.
- Validate the portable YAML value subset using the existing YAML libraries and their
  representation or event APIs where materialization would erase evidence.
  Reject unsupported values; do not replace either parser.
- Apply simple byte and nesting limits at artifact and schema entry points.
  Use one small helper per language and ordinary iterative traversal where needed.
- Compare presentation JSON structurally and use standards-based canonical JSON only for
  compiled-schema identity.
- Correct canonicalization, format, pattern, `SchemaView`, identity, compiler, and
  `enforced` behavior through the shared vectors named in the disposition table.

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

This minor release is a hard cut.
Define the final API once and remove replaced shapes instead of carrying aliases.

Known changes:

- Python `compile_model` requires `contract_id` and accepts optional `schema_id`.
- TypeScript `compileSchema` requires `contractId` and accepts optional `schemaId`.
- Structural validation accepts an optional explicit mapping of already-loaded schema
  resources; neither runtime retrieves a resource.
- `SchemaView.contract_id` no longer falls back to `$id`; both implementations expose a
  separate optional schema ID.
- Skill installation gains explicit scope, target selection, and dry-run options.
  An ambiguous invocation fails without writing.
- Machine-readable results retain stable codes and fields needed by consumers, but
  cross-runtime equality is structural rather than byte equality of pretty JSON.

The final package-root surface is:

| Capability | Python | TypeScript |
| --- | --- | --- |
| contracts and metadata | `Contract`, `Contracts`, `SchemaMetadata`, `SchemaProfile`, `SchemaStatus`, `SchemaWarning`, `WarningCode`, `parse_schema_metadata` | idiomatic type counterparts plus `Contracts`, `parseSchemaMetadata` |
| validation | result types, `validate_artifact`, `validate_values`, `validate_structural`, `validate_semantic`, `infer_envelope_key`, `EnvelopeAmbiguityError` | idiomatic type and function counterparts |
| compilation | `CompileResult`, `compile_model` | `CompileOptions`, `CompileResult`, `compileSchema` |
| schema navigation | `FieldInfo`, `SchemaView` | `FieldInfo`, `SchemaView` |
| authoring annotations | `SoftField`, `SoftOwner`, `SoftTier`, `RepairKind` | `softField`, `SoftFieldOptions`, `SoftOwner`, `SoftTier`, `RepairKind` |
| generated sections | `GeneratedSection`, `RegenerateResult`, `regenerate` | idiomatic type counterparts plus `regenerate` |

Canonicalization, enforcement transforms, JSON presentation helpers, schema hashing, raw
frontmatter parsing, engine-error normalization, `SoftFieldMeta`/`softFieldMeta`, and
generated-section parsing are internal implementation details and are not exported from
the package root.

The final CLI keeps `validate`, `compile`, `inspect`, `docs`, `generate`, `prime`,
`doctor`, and `skill`. `compile` requires `--contract` and accepts optional
`--schema-id`. `skill --install` requires `--scope project|personal`, accepts repeatable
`--agent portable|claude`, and supports `--dry-run`. No batch operands, discovery,
JSONL, SARIF, format negotiation, or legacy output switch is added.

Artifact results retain the existing contract, metadata, values, warning, structural,
and semantic fields and add one top-level `outcome` discriminator: `valid`, `invalid`,
or `input_error`. CLI exit classes derive only from that outcome (`0`, `1`, or `2`).
Presentation JSON is deterministic within a runtime but cross-runtime tests compare its
parsed structure. Compiled-schema digests use the shared canonical digest encoding.

Remove deprecated aliases, v0.2 compatibility exports, and alternate result projections
that are not part of this surface.
Internal helpers remain private unless there is a demonstrated host-library use case.

## Compatibility Policy

**Code types, methods, and function signatures:** DO NOT MAINTAIN. Ship one clean public
surface with no deprecated aliases or wrappers.

**Library APIs:** DO NOT MAINTAIN the old signatures when an accepted design correction
requires a better one.
Preserve capabilities, not historical call shapes.

**Server APIs:** N/A.

**File formats:** DO NOT MAINTAIN rejected or ambiguous forms.
Ship one documented Markdown/frontmatter profile and one pure-YAML profile.
The contract ID identifies the payload contract; do not add or accept a second artifact
version field.

**Database schemas:** N/A.

**CLI:** Preserve useful workflows, stable error codes, and the exit classes `0`
success, `1` validation/drift failure, and `2` invocation/input failure.
Flags and result fields may change when the final paired surface is simpler.
Do not retain hidden legacy flags or dual output modes.

Document all intentional breaks in one concise migration section and the release notes.
Do not implement migration behavior in the runtime.

## Implementation Plan

### Phase 1: Characterize and Simplify

- [x] Record the `main` baseline: public exports, CLI surface, documented artifact
  forms, test counts, source lines, and current validation commands.
- [x] Build a behavior inventory that maps each public guarantee to one primary test
  owner.
- [x] Run the existing Python, TypeScript, Node, Bun, golden, build, and package-smoke
  checks before changing behavior.
- [x] Reproduce each candidate hardening defect independently against `main`; reject or
  downgrade candidates that do not cross the stated trust model.
- [x] Complete the previous-PR disposition table: attach one minimal reproduction to
  every applicable row and confirm that every excluded row belongs only to discarded
  functionality or an out-of-scope threat.
- [x] Inventory the Python exports, TypeScript exports, CLI flags, and result fields;
  specify one final hard-cut surface and delete the need for deprecation shims.
- [x] Consolidate portable cases into shared YAML vectors without introducing a general
  conformance framework.
- [ ] Reduce CLI goldens to the smallest broad scenarios that retain command, output,
  side-effect, and exit coverage.
- [ ] Remove redundant tests only after a coverage map shows the retained owner catches
  the same regression.
- [ ] Record the accepted fix list, rejected findings, and measured complexity budget in
  this spec before Phase 2 implementation.

**Phase gate:** every applicable row has a reproduction, trust-boundary statement,
failing test, proposed primary owner, and minimal implementation sketch.
Every prior-PR runtime change has a recorded disposition.
Existing user capabilities remain covered, and the final hard-cut public surface is
explicit.

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
- [ ] Require a final senior review focused on the hard-cut API, threat-model fit, test
  ownership, and total design complexity.

**Phase gate:** every retained capability and the final documented hard-cut behavior
passes; every accepted defect is fixed; both packages build and install; the exact
artifacts pass smoke tests; no prohibited subsystem exists; and the complexity limits
are satisfied.

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
- direct compiled-schema semantic and canonical-digest comparison
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
Release Python and TypeScript together as a new minor version under their existing
shared package version policy.
This is a deliberate hard cut, not a patch-compatible migration.

Keep the prior hardening PR open only as an evidence source until the replacement work
has captured every accepted finding.
Then close it without merging.

## Success Criteria

- Useful capabilities and workflows from `main` are preserved through one clean public
  surface; no deprecated compatibility code remains.
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
The release is a hard-cut minor version.
If implementation finds two materially different clean public designs, pause with
minimal examples and the tradeoff; do not solve the ambiguity by shipping both.

## References

- [Softschema Guide](../../../softschema-guide.md)
- [Softschema Spec](../../../softschema-spec.md)
- [Development](../../../development.md)
- [Python Package Design](../../../softschema-python-design.md)
- [TypeScript Package Design](../../../softschema-typescript-design.md)
- [Prior Full Engineering Review](../../reviews/review-2026-06-10-softschema-full-eng-review.md)
- [Prior Review Remediation Plan](plan-2026-06-10-softschema-review-remediation.md)
- [Previous hardening PR #20](https://github.com/jlevy/softschema/pull/20)
- tbd `general-testing-rules`
- tbd `golden-testing-guidelines`
- tbd `common-doc-guidelines`
- tbd `supply-chain-hardening`

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
