---
title: Actual Validation Execution and Result Migration
description: Replace the unreleased mechanism hierarchy with execution evidence on independent structural and semantic checks.
date: 2026-09-12
status: Implemented and source-integrated; coordinated release pending
upstream_pr: https://github.com/jlevy/softschema/pull/59
baseline: main at bb8617aa7249096eec39e1f45d0b245289ede651
---
# Actual Validation Execution and Result Migration

## Problem and Decision

A result must distinguish a check that accepted a payload from one that never ran.
PR 59 at review revision `0dfbe95` reported a single `enforcement_applied` value:
`schema`, `model`, or `none`. Both validators can run, however, and a model can reject a
payload its schema accepts.
Reporting `schema` cannot establish that the overall verdict is reproducible from the
compiled schema. TypeScript also mistook a model label for an invoked model, and both
runtimes reported schema preparation failures as an applied schema.
The implementation below resolves these defects.

Use the existing independent `structural` and `semantic` result records.
Add an `execution` field to each and remove the unreleased `enforcement_applied` field
and type. The spec remains the authority for the public definitions.
This plan records the migration and verification decisions.

A downstream consumer verified source integration against `b494f72`; the coordinated
package release remains open.

## Public Contract

`ValidationExecution` is a public type with three values:

| Value | Evidence |
| --- | --- |
| `not_run` | No payload validator was invoked. Existing errors and skip reasons distinguish an absent binding, an artifact failure before extraction, and failed schema preparation. |
| `completed` | A payload validator completed its verdict. Existing `ok` distinguishes acceptance from rejection. |
| `errored` | Payload evaluation began but did not produce a completed verdict. Existing errors report the failure where the API returns such a result. |

Assign this state at the actual invocation and completion boundaries.
Do not infer it from a path, a model label, `ok`, the absence of a skip reason, or an
error kind. The result of each check is independent, including when the other check
fails.

Three existing inputs retain distinct meanings:

- The artifact’s `softschema.status` is the author’s declared maturity or mode.
- The result’s `status` is the effective mode, after caller and registry precedence.
  `enforced` selects the checked schema overlay; it is not an attestation of execution.
- A trusted schema/model binding specifies a required check.
  An absent required schema still produces its error.
  A TypeScript model label alone supplies no validator.

No new artifact metadata, policy language, or aggregate enforcement level is introduced.
Hosts that require specific checks must supply trusted bindings, then verify execution
in the result or pass an opt-in caller requirement (`require`, `validate --require`)
that fails any required layer that did not complete.
Without that requirement, a generic metadata-only CLI check can remain valid without
establishing payload validity.

Keep `ok`, error records, skip reasons, and CLI exit classes.
A completed rejection is evidence of execution and remains invalid.
A failed preparation is not a payload rejection.
A skipped check never satisfies a host requirement for a completed check.

Unexpected semantic callback exceptions continue to propagate.
Do not catch programmer errors just to produce JSON; if the call raises, no completed
artifact report exists.
Structural evaluation already returns classified failures, so it can return `errored`
without introducing a new exception policy.

## Failure and Portability Rules

| Input or event | Structural execution | Semantic execution | Result |
| --- | --- | --- | --- |
| Artifact read, format, metadata, or envelope failure | `not_run` | `not_run` | Preserve existing failure result or CLI input error. |
| Metadata-only artifact in effective `enforced` mode | `not_run` | `not_run` | Format/metadata valid, with shortfall warning. |
| Caller requires a layer that did not complete | Actual invocation state | Actual invocation state | Required layer not ok with an appended `check_not_completed` error; outcome invalid. |
| Missing, malformed, or unsupported schema fails preparation | `not_run` | Actual model result, if supplied | Preserve schema error and invalid outcome. |
| Schema accepts, no model | `completed` | `not_run` | Valid. |
| Schema rejects | `completed` | Actual model result, if supplied | Invalid. |
| Both checks accept | `completed` | `completed` | Valid. |
| Schema accepts, model rejects | `completed` | `completed` | Invalid; semantic error remains visible. |
| Evaluation encounters an unresolved reference | Actual invocation state | Actual model result, if supplied | Preserve reference error and invalid outcome. |
| TypeScript has only a model label | Actual schema result | `not_run` | Never claim semantic execution. |
| TypeScript receives an actual model without a label | Actual schema result | `completed` if it returns | Record the actual model verdict. |
| CLI source model cannot be loaded | No payload check is invoked by that command | No payload check is invoked by that command | Preserve CLI error; no fabricated validation report. |
| Unexpected semantic exception | Earlier check may have completed | No returned semantic verdict | Raise; never manufacture acceptance or rejection. |

Python resolves some raw-mode references during `iter_errors`; Ajv resolves them while
compiling. For `$ref: '#/$defs/Missing'`, truthful progress is therefore `errored` in
Python and `not_run` in TypeScript.
Keep the common state definitions and make this engine difference explicit in shared
test expectations. Ordinary successful and rejected payload checks retain cross-runtime
result parity. Do not manufacture equal progress or add an eager schema traversal solely
to hide the implementation difference.

Warnings use effective mode and actual completed checks.
If a model ran after schema preparation failed, report the missing structural guarantee
without denying the model check.
Failure before payload extraction has no shortfall warning to qualify a payload verdict.
Preserve the two warning codes introduced by PR 59, with messages that describe
completed checks rather than a winning mechanism.

## Compatibility and Release

| Boundary | Migration |
| --- | --- |
| Existing artifacts read by the new runtime | No rewrite: metadata keys, contract IDs, profiles, compiled schema format, and validation modes remain unchanged. |
| New artifacts read by an old runtime | This change writes no new artifact metadata. Artifacts using existing models and schemas remain readable. Independently evolving payload contracts still require their own contract version. |
| New serialized validation results | Layer records gain `execution`; the unreleased aggregate field is removed. Strict result consumers must adopt the new record shape. |
| Old serialized validation results | Absence of `execution` means historical execution is unknown. Preserve absence or rerun validation; never infer an execution state from `ok`, `engine`, or skip reasons. No result-deserialization migration framework is added. |
| Public Python result constructors | Require `execution` explicitly as a keyword-only argument. Update manual constructors and fixtures rather than silently inventing a default. |
| Public TypeScript interfaces | Require the same field on manually constructed layer records. |
| Validation function callers | Existing arguments and default verdict rules remain supported. The optional `require` argument rejects checks that did not complete. TypeScript structural skip reasons now follow the supplied semantic validator, not its label. |

Two repair-result corrections share this release boundary.
Python callers passing `model=` to `repair_and_validate_artifact` receive a final
semantic verdict from that model, even when their `Contract` has no model or names a
different one; the caller’s contract is not mutated.
TypeScript callers repairing a missing or invalid-UTF-8 file without a contract receive
`input_error` instead of `invalid`. Existing artifact bytes and bindings need no
migration. Consumers of stored results should preserve historical verdicts as recorded,
and revalidate when they need the corrected semantics.

The new field is under Unreleased and has no containing release tag at the baseline.
Do not keep a compatibility alias for it.
Released result constructors are a source compatibility boundary, so prepare this API
change for the next minor release, **0.9.0**, under the existing
[publishing process](../../../publishing.md).
Both packages must release together.
Version bumps, tags, publication, and downstream released dependency-range updates are
release work; this implementation does not publish or change dependency lockfiles.

Metaproc’s manual serializer must forward both complete layer records, including
structural skip reasons.
`dataclasses.asdict` preserves the native fields of both old and new SoftSchema versions
without fabricating evidence for an older version.
Consumers must tolerate historical reports without execution fields and must require new
evidence only for newly run checks under an upgraded validator.

Consumers whose bindings and loaders supply models and compiled schemas and consume
`ok`, values, and layer errors keep that behavior.
Their existing artifact files need no format migration.

Metaproc’s built-in model-only bindings keep their existing validation behavior and
`document-enforcement-via-model-only` advisory.
Their structural check is `not_run` with `inferred_via_model`; the supplied model’s
acceptance or rejection is a `completed` semantic check.
The structural `engine` label still names the configured engine and does not establish
execution. Adding compiled schemas or requiring a structural check would change those
bindings’ contract and is a separate migration.

## Implementation and Verification

- [x] Add failing shared execution vectors and runtime-specific model/exception cases.
- [x] Implement explicit layer execution in Python and TypeScript, including lower-level
  validation, values, artifacts, pre-payload failures, and repair.
- [x] Replace the unreleased hierarchy and update public exports and explicit
  constructor call sites.
- [x] Revise the spec, guides, design references, changelog, source skill and generated
  mirrors, and broad CLI journeys.
- [x] Verify frozen Python tests and lint; TypeScript lint, types, coverage, build, and
  package checks; every golden runtime and cross-implementation output comparison.
- [x] Verify source integration of the exact commit in Metaproc and a downstream
  consumer.
- [x] Add an opt-in caller requirement for completed checks, with shared vectors, CLI
  journeys, and documentation.
- [ ] Publish coordinated 0.9.0 releases and migrate released consumer dependency
  ranges; this remains separate from source implementation completion.

Shared vectors own portable evidence cases; adapter tests own model identity, callback
exceptions, and engine-specific progress.
Extend the existing per-language model CLI journeys with a semantic rejection beside a
structural success. Regenerate whole result transcripts through the configured golden
runner, review the changes, and retain the existing golden fixture ownership rules.

## Verification Record

Downstream integration exposed a compatibility defect in the checked overlay: a nullable
model containing another nullable, explicitly closed model was refused because the
compiler added redundant closure to the inner nullable wrapper.
The compiler now recognizes a pure reference plus a null-only branch in `anyOf` or
`oneOf`, with annotation-only siblings.
It preserves the referenced object’s explicit closure or opt-out and retains the
existing analysis for other composition.
Five shared vectors cover nested models, null, unknown-property rejection, explicit open
policy, and validation siblings.
Existing files require no rewrite.

Downstream verification also found manual layer-result constructors that need the
required field. A parsing or binding error raised before either check runs records both
layers as `not_run` explicitly, and code that rewrites a native result preserves its
actual check records, for example through `dataclasses.replace`.

The source at `b494f72` passes 251 Python tests and the complete Python lint suite
(Ruff, BasedPyright, codespell, documentation footers, and retired-surface checks).
TypeScript passes lint, types, 263 tests, build, and package publication lint;
`validate.ts` has 100% line coverage.
Fourteen shared vectors cover independent execution, with adapter cases for actual model
identity and callback failures.

CLI verification passes all 82 Python, 80 Node, and 82 Bun journey commands.
Both language-specific model journeys retain a completed structural acceptance beside a
completed semantic rejection.
Two existing repair byte assertions now print portable hex bytes instead of depending on
BSD/GNU `od -c` spacing.
The shared parser-error message remains elided because its wording is language-specific.
All 25 direct Python-versus-Node comparisons pass, including bundled documentation and
skill output.

Metaproc’s serializer integration passed 96 tests against this source through native
dataclass forwarding.
Revision `b494f72` passed all eighteen hosted checks, including both language suites,
shared journeys and package smoke tests across operating systems.

Follow-up verification of host-required checks at `445ec92`, with isolated skill-install
test fixtures, passes 257 Python tests and 297 TypeScript tests, lint, types, and
coverage. All 85 Python, 83 Node, and 85 Bun golden commands and 27 direct
cross-implementation comparisons pass.
Local wheel, source-distribution, and npm-tarball installations pass the quickstart,
both artifact profiles, required structural validation, bundled-resource access, and
skill bootstrap checks.
This local verification does not replace the hosted operating-system matrix or the
coordinated release gate.

Follow-up repair tests cover a model supplied separately from a model-free or
differently bound `Contract`, including acceptance, rejection, scalar conformance,
unchanged `write=False` bytes, and callback exceptions.
Both runtimes also check missing-file, invalid-UTF-8, and parse-failure outcomes without
an inferred contract.
A shared CLI journey pins the missing-file result with both layers `not_run`. Local
checks pass 268 Python tests, 303 TypeScript tests, 86 Python, 84 Node, and 86 Bun
golden commands, and 27 direct Python–Node parity comparisons.
The golden commands used an installed `tryscript` 0.1.7 because the sandbox could not
download the configured 0.2.1 runner; hosted CI must confirm the configured runner.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
