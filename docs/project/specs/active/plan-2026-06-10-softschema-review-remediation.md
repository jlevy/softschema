# Feature: Softschema Review Remediation (Quality, Parity, and Design Alignment)

**Date:** 2026-06-10 (last updated 2026-06-10)

**Author:** Claude Code, with maintainer decisions by Joshua Levy

**Status:** In Review

## Overview

A single phased plan to execute the findings of
[review-2026-06-10-softschema-full-eng-review.md](../../reviews/review-2026-06-10-softschema-full-eng-review.md).
The phases are ordered so cleanup lands first, then the parity and test safety net makes
refactoring safe (TDD on the golden corpus), then the major design changes land on that
safety net, then the remaining medium-priority items finish the pass.

## Goals

- Fix every reproduced bug and user-facing breakage from the review.
- Make “exact behavioral parity” an enforced invariant: the golden corpus runs under
  Node (the published runtime) as well as Bun, scenarios are the same files for both
  CLIs wherever possible, and known Python/JS divergences are closed or pinned by
  fixtures.
- Implement the decided design changes: `status: enforced` gets optional teeth,
  envelope/binding inference moves into the libraries, the spec’s metadata rules are
  enforced, and a metadata-only validate mode serves the soft stage.
- Bring the docs back in line with shipped reality (the TypeScript port) and calibrate
  the parity claims.

## Non-Goals

- New artifact-format features beyond the spec alignment above (no data-sidecar loader,
  no repair loop, no body parsing; the spec’s v0.1 out-of-scope list stands).
- Loosening behavior under `soft` or `permissive`: the `status` decision adds strictness
  only at `enforced` and changes nothing else.
- A semantic-layer counterpart to the `enforced` overlay (per-call `extra="forbid"`
  injection into Pydantic/Zod models); enforcement acts at the structural layer against
  the schema sidecar.

## Background

The full review found the implementation healthy (all tests green, strong supply-chain
posture, real parity machinery) but identified: shared spec violations, unhandled CLI
error paths, a broken npm agent bootstrap, parity enforced only for the corpus’s input
ranges and only under Bun, and post-TypeScript doc staleness.

Two maintainer decisions shape this plan:

- **`status` gets optional teeth.** When the effective status is `enforced`, structural
  validation treats object schemas that declare `properties` but omit
  `additionalProperties` as `additionalProperties: false`; explicit
  `additionalProperties` always wins; `soft`/`permissive` are unchanged.
  Enabling strictness enforces it; not wanting enforcement means not enabling it.
- **Exact parity is the requirement.** Golden tests are the same files for both CLIs
  whenever possible, the corpus runs on the published runtimes, and functionality is
  exposed through the CLI so the shared corpus can hold it to parity.

The phase order exists so each phase makes the next one safer: quick fixes remove noise,
the expanded corpus pins behavior before refactors, the refactors land golden-first, and
the long tail follows.

## Design

### Approach

Every behavior change follows the golden-first parity loop in
[development.md](../../../development.md#keeping-python-and-typescript-in-parity): write
or update the shared scenario, implement in Python, port to TypeScript, and require both
golden runs plus the conformance test green.
Phase-1 bug fixes that change no specified behavior land with regression tests in the
per-language suites instead.

### Components

- `packages/python/src/softschema/` and `packages/typescript/src/`: CLI error
  boundaries, the `enforced` overlay, binding inference, metadata rules.
- `tests/golden/`: corpus expansion, same-file scenarios, new fixtures.
- `tests/golden/run.sh` and `.github/workflows/ci.yml`: Node golden runs, Python matrix
  golden runs, cross-implementation diff job.
- `docs/`: spec, guide, design docs, README calibration.
- `skills/softschema/` and the `skill --install` flow: marker stamping, drift tests.

### API Changes

- `validate_structural` / `validateStructural` gain a strict-extras option (the
  `enforced` overlay); a shared `apply_enforced_extras` / `applyEnforcedExtras`
  transform is exported from the canonicalize module of each package.
- Binding inference (contract from metadata, status resolution, single-key envelope
  inference with ambiguity rejection) becomes library API in both packages; the CLIs
  call it instead of reimplementing it.
- `softschema validate` accepts invocation without `--model`/`--schema` as a
  metadata-only check (exact flag shape decided in phase 3).
- Both CLIs gain `--version`.

## Implementation Plan

### Phase 1: Quick Fixes and Bug Repairs

Low-risk, independently shippable corrections; each lands with a regression test.

- [ ] Python CLI error boundary: catch `OSError`, `FmFormatError`, `YAMLError`,
  `ModuleNotFoundError`/`ImportError`, `TypeError`, `ValueError`, and `ValidationError`
  in `validate`, `compile`, `inspect`, and `generate`; one-line stderr message and exit
  2 (no tracebacks for user mistakes).
- [ ] `validate_artifact` (and the TypeScript `validateArtifact`) return a structured
  `parse_error` result for missing/unreadable files instead of raising.
- [ ] `generate` exit codes: runtime errors exit 2; reserve 1 for drift; convert the
  vocab-pointer `KeyError` into a clean error.
- [ ] TypeScript CLI exit hygiene: set `process.exitCode` instead of `process.exit()`
  after async work; add EPIPE handlers on stdout/stderr; handle SIGINT with exit 130.
- [ ] TypeScript: replace `(err as Error).message` casts with
  `err instanceof Error ? err.message : String(err)`.
- [ ] TypeScript: parse schema sidecars through the `parseYaml` wrapper and reject
  non-mapping roots with a clean structural error.
- [ ] Add the agent `--help` epilog to the TypeScript CLI (same text as Python).
- [ ] Ship `docs/softschema-typescript-design.md` in the wheel; add
  `examples/movie_page/movie-page.schema.yaml` to the npm resources; add a test in each
  package that every `DOC_TOPICS` entry resolves from the built artifact.
- [ ] `--version` on both CLIs.
- [ ] Atomic writes in `_install_skill` (use `atomic_write_text`, matching compile and
  generate).
- [ ] `_dev_repo_root` and the TypeScript resource walk-up: fail with a clear error
  instead of guessing (`parents[4]`, magic depth 6 becomes a named constant).
- [ ] Trivial cleanups: `devtools/lint.py` explicit UTF-8 encoding, `dedent` for the
  brief-skill string, pytest `python_files` back to `test_*.py`, remove the dead
  `FieldInfo` re-export and the dead `order !== null` check, escape `|` in generated
  enum tables.

### Phase 2: Parity and Test Safety Net

Full coverage of testing and feature parity on essential features, so phase 3 refactors
are TDD against the corpus.
Behavior-affecting divergence fixes here go golden-first.

- [ ] `tests/golden/run.sh`: `SOFTSCHEMA_IMPL=ts` runs `node dist/cli.js` (the published
  runtime) and `SOFTSCHEMA_IMPL=ts-bun` runs `bun dist/cli.js`; per-impl scenario
  directories map `ts-bun` onto `scenarios-ts/`.
- [ ] CI: the typescript job runs the golden corpus under both Node (pinned via
  setup-node) and Bun; the golden job runs the Python corpus across the supported Python
  matrix, not only 3.13.
- [ ] CI: add a direct cross-implementation diff step that runs both CLIs on the same
  inputs in one job and byte-compares the outputs, so parity failures are reported as
  parity failures rather than as one side drifting from the committed corpus.
- [ ] Expand the shared corpus with edge-case fixtures: non-ASCII values, empty and
  whitespace-only frontmatter, unterminated fences, nested validation errors, max-side
  keywords (`maxLength`, `maxItems`, `pattern`, `exclusiveMaximum`), a pure-yaml
  scenario, per-impl semantic (`--model`) scenarios with identical output, and at least
  one full (un-elided) `docs <topic>` content check.
- [ ] Close the divergences the new fixtures expose: `pyRepr` number formatting
  (exponent padding, Python’s 1e16 exponential threshold, `inf`/`nan`), the
  empty-frontmatter `?? {}` coercion, the unterminated-fence error kind, `augmentSchema`
  merge-vs-replace, and the quoting/`got list` wording of out-of-corpus error messages.
  Document any remaining number-format limitation (the `2.0` family) in
  `tests/golden/README.md` with the full list of values the corpus must avoid.
- [ ] Per-language test gaps: TypeScript `generate.ts` error paths, pure-yaml parse
  error, `skill --install`, and a TypeScript mirror drift test equivalent to
  `test_skill_mirror_drift.py`; include `test/` in the TypeScript typecheck.

### Phase 3: Major Design Changes (Highest Priority)

All items follow the golden-first loop and update the spec, guide, and design docs in
the same change.

- [ ] **`status: enforced` teeth (decided).** Add `apply_enforced_extras` /
  `applyEnforcedExtras` to the canonicalize modules (recursive overlay: object schemas
  with `properties` and no explicit `additionalProperties` validate as closed; explicit
  values win; free-form mappings untouched; validation-time only).
  Thread it through `validate_structural` when the effective status is `enforced`. New
  golden scenario: the same extras-carrying document passing under `status: permissive`,
  failing under `--status enforced`, and failing under a document-declared `enforced`.
  Rewrite the spec’s Status Values section (drop “does not change validation behavior by
  itself”), the guide’s promotion playbooks, and the design docs’ status wording to
  match.
- [ ] **Binding inference into the libraries.** Move contract/status/envelope resolution
  (single-key inference, ambiguity rejection per the spec) from the CLIs into library
  API in both packages; CLIs become thin callers; the document is read once.
  Library callers with no `envelope_key` get spec behavior (inference or rejection)
  instead of merged multi-key payloads.
- [ ] **Pure-yaml profile alignment.** Honor the spec’s stated rule: recognize the
  `softschema:` metadata block at the document root and apply the same envelope rules;
  reject the block being validated as payload.
  (If implementation reveals this is the wrong call, amend the spec instead; see Open
  Questions.)
- [ ] **Metadata rules enforced.** Reject unknown keys in the `softschema:` block in
  both implementations; define the contract-ID minimum in the spec (non-empty string,
  recommended form documented as advisory) and validate it.
- [ ] **Metadata-only validate.** `softschema validate` without `--model`/`--schema`
  checks the metadata block, contract ID shape, and envelope presence/uniqueness, so the
  CLI is useful from the `soft` stage onward.

### Phase 4: Remaining Items

Cleanups, clarifications, and the rest of the testing and packaging improvements.

- [ ] Doc refresh for the TypeScript port: guide ("What Softschema Is", “Relationship To
  The Python Package”, Further Reading, the CLI list), python-design (module table
  `stage` ghost, “future port” wording, Accepted/Deferred entries), mark the
  public-readiness plan superseded, rewrite publishing.md to present state, link
  publishing-npm.md, drop the duplicate AGENTS.md footer, update the development.md CI
  snippet pins.
- [ ] README calibration: replace “unreasonably effective”, phrase the sidecar guarantee
  as content-identical with equal `schema_sha256`, shorten the duplicated movie artifact
  to a fragment plus link.
- [ ] Spec polish: one-paragraph conformance-language note.
- [ ] Skill hardening: format/version stamp on the DO NOT EDIT marker (wire the
  currently dead `<version>` substitution or delete it and its vacuous test assertions),
  `allowed-tools` in the skill frontmatter, git-root awareness for `skill --install`,
  carry the `@latest` cool-off justification (or a pin) in the skill text.
- [ ] Resource unification: one manifest consumed by the wheel force-include, the npm
  copy-resources script, and `DOC_TOPICS`; drop or sanitize the `agents` and
  `publishing` topics (strip the tbd integration block from bundled copies).
- [ ] Library polish: cache the Ajv instance/compiled validators, decide the node-free
  `"."` entry vs documented Node-only posture plus a `"./cli"` export, resolve the
  half-exported `readFrontmatter`.
- [ ] Test polish: rename `coverage.test.ts` to reflect its content, capture rather than
  discard stdout in the in-process CLI test, document the corpus update workflow in
  `tests/golden/README.md`.

## Testing Strategy

- Phase gates: CI fully green after each phase; phase 3 does not start until the phase-2
  corpus and cross-implementation diff job are in place, so every refactor is TDD
  against pinned parity behavior.
- Golden-first for all specified behavior; per-language regression tests for phase-1
  fixes (every reproduced traceback gets a test that asserts the clean message and exit
  code).
- The cross-implementation diff job is the backstop for anything the committed corpus
  misses: identical inputs, byte-compared outputs, run on Node for TypeScript.

## Rollout Plan

- Each phase is one PR (or a small stack), merged in order; the branch for this plan
  starts from the review PR.
- Phases 1 and 2 are release-safe at any point (patch release).
  Phase 3 changes specified behavior (`enforced` strictness, metadata rejection, library
  envelope rules) and ships as a minor version bump with release notes calling out the
  changes; both packages release together under the same version as usual.

## Open Questions

- Pure-yaml: the plan implements the spec’s stated rule (metadata block plus envelope
  rules at the root). Confirm, or prefer amending the spec to today’s
  whole-root-as-payload behavior?
- The `values` block of validation output can embed numbers whose Python and JS
  serializations differ (`1e-07` vs `1e-7`). Close it with a Python-format number
  serializer on the TypeScript side, or document the value ranges as a known limitation?
  (Error-message formatting via `pyRepr` is being fixed either way.)
- Dropping the `agents`/`publishing` doc topics changes the public `docs` surface.
  Acceptable in the same minor bump as phase 3?

## References

- [Full engineering review](../../reviews/review-2026-06-10-softschema-full-eng-review.md)
- [Prior docs/design review](../../reviews/review-2026-05-26-softschema-docs-design.md)
- [Parity development process](../../../development.md#keeping-python-and-typescript-in-parity)
- [Softschema Spec](../../../softschema-spec.md)
- [TypeScript/Zod parity plan](plan-2026-06-01-softschema-typescript-zod-parity.md)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
