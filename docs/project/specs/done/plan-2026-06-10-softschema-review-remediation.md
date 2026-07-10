# Feature: Softschema Review Remediation (Quality, Parity, and Design Alignment)

**Date:** 2026-06-10 (last updated 2026-06-10)

**Author:** Claude Code, with maintainer decisions by Joshua Levy

**Status:** Complete (2026-06-11). All four phases and the three original follow-up
beads landed or were explicitly closed.

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
**Status: complete (2026-06-10).** All items below landed; full Python suite (101),
TypeScript suite (99) and the golden corpus (14/14 against both implementations) are
green, lint and typecheck clean.
Beads ss-5ipx, ss-m776, ss-i693, ss-29i1, ss-r4rs, ss-nqx0 closed.
Cross-CLI exit-code parity for user errors (missing file, malformed metadata, bad model
spec, missing implementation) verified: both CLIs exit 2.

- [x] Python CLI error boundary: a shared `_USER_ERRORS` tuple and `_run_cmd` wrapper
  catch `OSError`, `FmFormatError`, `YAMLError`, `ModuleNotFoundError`/`ImportError`,
  `TypeError`, `ValueError`, `ValidationError`, and `KeyError` across every subcommand;
  one-line stderr message and exit 2 (no tracebacks for user mistakes).
- [x] `validate_artifact` (and the TypeScript `validateArtifact`) return a structured
  `parse_error` result for missing/unreadable files instead of raising.
- [x] `generate` exit codes: runtime errors exit 2; reserve 1 for drift; vocab-pointer
  lookup now raises `ValueError` (not `KeyError`).
- [x] TypeScript CLI exit hygiene: `process.exitCode` instead of `process.exit()` after
  async work; EPIPE handlers on stdout/stderr; SIGINT exits 130.
- [x] TypeScript: replaced `(err as Error).message` casts with an `errMessage` helper
  (`err instanceof Error ? err.message : String(err)`).
- [x] TypeScript: schema sidecars parse through the `parseYaml` wrapper; a non-mapping
  root returns a clean `schema_sidecar_invalid` structural error.
- [x] Agent `--help` epilog added to the TypeScript CLI (same text as Python), plus a
  top-level backstop so no command leaks a stack trace.
- [x] Shipped `docs/softschema-typescript-design.md` in the wheel; added
  `examples/movie_page/movie-page.schema.yaml` to the npm resources; a doc-topics test
  in each package asserts every `DOC_TOPICS` path resolves.
- [x] `--version` on both CLIs (prints `softschema <version>`).
- [x] Atomic writes in Python `_install_skill` (`atomic_write_text`). (TypeScript
  counterpart tracked separately as ss-oodd.)
- [x] `_dev_repo_root` and the TypeScript resource walk-up fail with a clear error
  instead of guessing (named `MAX_RESOURCE_WALK_DEPTH` constant).
- [x] Trivial cleanups: `devtools/lint.py` explicit UTF-8; `dedent` for the brief-skill
  string; pytest `python_files` back to `test_*.py`; removed the dead `FieldInfo`
  re-export and the dead `order !== null` check; escape `|` in generated enum tables.

### Phase 2: Parity and Test Safety Net

Full coverage of testing and feature parity on essential features, so phase 3 refactors
are TDD against the corpus.
This phase is **fundamental to stability and must land before Phase 3**: the golden
corpus is the safety net the design refactors are validated against, so it has to run on
the published runtime (Node) and cover the whole CLI surface before any behavior moves.
Behavior-affecting divergence fixes here go golden-first.

The headline item is **complete CLI golden coverage** (bead ss-q5wf): one tryscript
corpus, run against both CLIs, exercising every command, flag, and user-error exit path,
following `golden-testing-guidelines` (full output, no surgical extraction, patterns
only for genuinely variable fields such as the version string) and tryscript best
practices.

**Status: harness, CI, cross-impl diff, and complete CLI coverage complete
(2026-06-10).** The golden corpus runs under py, ts (Node, the published runtime), and
ts-bun (Bun); a direct cross-impl diff job byte-compares Python vs TypeScript/Node; the
Python golden corpus runs across the 3.11–3.14 matrix.
Beads ss-danw, ss-8jd1, ss-lxnd, ss-q5wf closed.
Running the corpus under Node surfaced a real divergence the Bun-only run hid: `compile`
imports a TypeScript model module, which plain Node cannot load, so the `.ts`-model
compile scenario now lives in `scenarios-ts-bun/` (proven under Bun and the conformance
unit test) while every runtime command runs under Node, plus a Node-safe
`validate --model` scenario using a plain `.mjs` Zod model.
The edge-case fixtures and divergence-closing (ss-3iz5) and the per-language test gaps
(ss-c71z) remain open and are **not** prerequisites for Phase 3 (they harden the net
further; the complete CLI coverage above is the prerequisite and is in place).

- [x] `tests/golden/run.sh`: `SOFTSCHEMA_IMPL=ts` runs `node dist/cli.js` (the published
  runtime), `ts-bun` runs `bun dist/cli.js`; per-impl directories are `scenarios-py`,
  `scenarios-ts` (Node-safe, run under ts and ts-bun), and `scenarios-ts-bun`
  (TS-runtime-only). (ss-danw)
- [x] CI: the typescript job runs the golden corpus under both Node (pinned via
  setup-node) and Bun; the golden job runs the Python corpus across the 3.11–3.14
  matrix. (ss-8jd1)
- [x] CI: `tests/golden/cross-impl-diff.sh` runs both CLIs on the same inputs in one job
  and byte-compares stdout and exit codes, so parity failures are reported as parity
  failures rather than as one side drifting from the committed corpus.
  (ss-lxnd)
- [x] **Complete CLI golden coverage** (ss-q5wf): every command and flag exercised on
  both CLIs, including the user-error exit paths Phase 1 made parity-clean (missing
  file, malformed frontmatter, malformed metadata, unknown topic, ambiguous envelope,
  missing implementation, envelope mismatch), `--version` (with a `[VERSION]` pattern),
  `docs <topic>` and `--list --json`, `skill` and `skill --brief`, `generate --check`
  (no-drift and drift), and per-impl semantic (`--model`) scenarios.
  Error scenarios whose stderr wording is engine-specific assert the stable
  `softschema <cmd>:` prefix and exit code, eliding the divergent tail; the divergent
  wording itself is the separate divergence-closing item below.
- [x] Edge-case fixtures that stress the corpus: non-ASCII values, empty and
  whitespace-only frontmatter, unterminated fences, nested validation errors, max-side
  keywords (`maxLength`, `maxItems`, `pattern`, `exclusiveMaximum`), a pure-yaml
  scenario, and at least one full (un-elided) `docs <topic>` content check.
- [x] Close the divergences the new fixtures expose: `pyRepr` number formatting
  (exponent padding, Python’s 1e16 exponential threshold, `inf`/`nan`), the
  empty-frontmatter `?? {}` coercion, the unterminated-fence error kind, `augmentSchema`
  merge-vs-replace, and the quoting/`got list` wording of out-of-corpus error messages.
  Document any remaining number-format limitation (the `2.0` family) in
  `tests/golden/README.md` with the full list of values the corpus must avoid.
  (ss-3iz5)
- [x] Per-language test gaps: TypeScript `generate.ts` error paths, pure-yaml parse
  error, `skill --install`, and a TypeScript mirror drift test equivalent to
  `test_skill_mirror_drift.py`; include `test/` in the TypeScript typecheck.
  (ss-c71z)

### Phase 3: Major Design Changes (Highest Priority)

All items follow the golden-first loop and update the spec, guide, and design docs in
the same change.
**Status: complete (2026-06-10)** along with the remaining Phase 2 items
(ss-3iz5 divergence closing, ss-c71z per-language test gaps, ss-oodd atomic TS skill
writes). Notes against the original sketch: the binding-inference work landed the
spec-conformance half (library-level single-key inference with `envelope_ambiguous` /
`envelope_missing` rejection, shared `infer_envelope_key` API that both CLIs delegate
to); the single-read CLI plumbing remains a deferred efficiency polish.
The pure-yaml open question resolved to amending the spec: the metadata block is
recognized at the root (same metadata rules), an explicit envelope nests the payload,
and otherwise the whole remaining root is the payload, since single-key inference would
break the data-sidecar use case the profile exists for.
Verified end to end: pytest 122; bun test 140 + typecheck; golden py 34 / ts(Node) 32 /
ts-bun 34; cross-impl diff byte-identical; lint clean.

- [x] **`status: enforced` teeth (decided).** Add `apply_enforced_extras` /
  `applyEnforcedExtras` to the canonicalize modules (recursive overlay: object schemas
  with `properties` and no explicit `additionalProperties` validate as closed; explicit
  values win; free-form mappings untouched; validation-time only).
  Thread it through `validate_structural` when the effective status is `enforced`. New
  golden scenario: the same extras-carrying document passing under `status: permissive`,
  failing under `--status enforced`, and failing under a document-declared `enforced`.
  Rewrite the spec’s Status Values section (drop “does not change validation behavior by
  itself”), the guide’s promotion playbooks, and the design docs’ status wording to
  match.
- [x] **Binding inference into the libraries.** (Single-read CLI plumbing deferred:
  ss-hvqw.) Move contract/status/envelope resolution (single-key inference, ambiguity
  rejection per the spec) from the CLIs into library API in both packages; CLIs become
  thin callers; the document is read once.
  Library callers with no `envelope_key` get spec behavior (inference or rejection)
  instead of merged multi-key payloads.
- [x] **Pure-yaml profile alignment.** (Resolved by amending the spec; see the status
  note above.) Honor the spec’s stated rule: recognize the `softschema:` metadata block
  at the document root and apply the same envelope rules; reject the block being
  validated as payload.
  (If implementation reveals this is the wrong call, amend the spec instead; see Open
  Questions.)
- [x] **Metadata rules enforced.** Reject unknown keys in the `softschema:` block in
  both implementations; define the contract-ID minimum in the spec (non-empty string,
  recommended form documented as advisory) and validate it.
- [x] **Metadata-only validate.** `softschema validate` without `--model`/`--schema`
  checks the metadata block, contract ID shape, and envelope presence/uniqueness, so the
  CLI is useful from the `soft` stage onward.

### Phase 4: Remaining Items

Cleanups, clarifications, and the rest of the testing and packaging improvements.
**Status: complete (2026-06-11).** Docs refreshed for the TypeScript port and
calibrated; spec gained a conformance-language note; skill hardened (allowed-tools,
format=f01 marker stamp, git-root-aware install, @latest cool-off justification in the
skill text); TS library polished (cached Ajv validators, `./cli` export,
`readFrontmatter` made public, Node-only posture documented); test polish (renamed
`coverage.test.ts` to `lib-units.test.ts`, in-process CLI test captures stdout instead
of globally stubbing); and a wheel force-include coverage test guards the resource
manifest against drift.
The bundled-topic trim (dropping/sanitizing the maintainer-facing `agents` and
`publishing` `docs` topics) was deliberately deferred: it changes the public `docs`
surface and is better treated as a separate product decision; the drift guard is in
place. Beads ss-hgsk, ss-pcqo, ss-jauz, ss-s0lt, ss-3m4s, ss-gyjs, ss-fuv1 closed.

- [x] Doc refresh for the TypeScript port: guide ("What Softschema Is", “Relationship To
  The Python Package”, Further Reading, the CLI list), python-design (module table
  `stage` ghost, “future port” wording, Accepted/Deferred entries), mark the
  public-readiness plan superseded, rewrite publishing.md to present state, link
  publishing-npm.md, drop the duplicate AGENTS.md footer, update the development.md CI
  snippet pins.
- [x] README calibration: replaced “unreasonably effective” and phrased the sidecar
  guarantee as content-identical with equal `schema_sha256`. (Shortening the duplicated
  movie artifact deferred as a maintainer content decision: ss-lflv.)
- [x] Spec polish: one-paragraph conformance-language note.
- [x] Skill hardening: `format=f01` stamp on the DO NOT EDIT marker; the dead
  `<version>` substitution and its vacuous test assertions deleted; `allowed-tools` in
  the skill frontmatter; git-root awareness for `skill --install`; the `@latest`
  cool-off justification carried in the skill text.
- [x] Resource unification: a wheel force-include coverage test now guards `DOC_TOPICS`
  against manifest drift.
  (The single shared manifest and the `agents`/`publishing` topic trim are deferred as a
  product decision: ss-8131.)
- [x] Library polish: cache the Ajv instance/compiled validators, decide the node-free
  `"."` entry vs documented Node-only posture plus a `"./cli"` export, resolve the
  half-exported `readFrontmatter`.
- [x] Test polish: rename `coverage.test.ts` to reflect its content, capture rather than
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
