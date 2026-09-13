---
title: Actual Validation Execution and Result Migration
description: Replace the unreleased mechanism hierarchy with execution evidence on independent structural and semantic checks.
date: 2026-09-12
status: Implemented; downstream integration and release pending
upstream_pr: https://github.com/jlevy/softschema/pull/59
baseline: 0dfbe95f4083678d61a379f26822c05ce32eb508
downstream_integration_pr: https://github.com/finterm-ai/trading/pull/525
tracking: [trading-jrva, trading-pkyo, trading-2rc2, trading-y277, trading-44ot]
---
# Actual Validation Execution and Result Migration

## Problem and Decision

A result must distinguish a check that accepted a payload from one that never ran.
The current PR reports a single `enforcement_applied` value: `schema`, `model`, or
`none`. Both validators can run, however, and a model can reject a payload its schema
accepts. Reporting `schema` cannot establish that the overall verdict is reproducible
from the compiled schema.
TypeScript also mistakes a model label for an invoked model, and both runtimes report
schema preparation failures as an applied schema.

Use the existing independent `structural` and `semantic` result records.
Add an `execution` field to each and remove the unreleased `enforcement_applied` field
and type. The spec remains the authority for the public definitions.
This plan records the migration and verification decisions.

PR 525 pins the baseline above.
That selects source, but does not resolve these defects or establish a release.
Integration must advance the gitlink after this implementation and its consumer checks
pass.

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

No new artifact metadata, policy language, additional check list, or aggregate
enforcement level is introduced.
Hosts that require specific checks must supply and verify their trusted bindings.
A generic metadata-only CLI check can remain valid without establishing payload
validity.

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
| Validation function callers | Keep callable arguments, verdict rules, error shapes, and skip reasons. |

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

Trading’s V3 bindings and loaders currently supply models and compiled schemas and
consume `ok`, values, and layer errors.
Keep that behavior while advancing exact source pins and verifying the serializer and
consumers. No artifact-format migration is needed for PR 525’s existing files.

## Implementation and Verification

- [x] Add failing shared execution vectors and runtime-specific model/exception cases
  (`trading-jrva`, `trading-pkyo`, `trading-2rc2`).
- [x] Implement explicit layer execution in Python and TypeScript, including lower-level
  validation, values, artifacts, pre-payload failures, and repair (`trading-jrva`,
  `trading-pkyo`, `trading-2rc2`).
- [x] Replace the unreleased hierarchy and update public exports and explicit
  constructor call sites (`trading-2rc2`).
- [x] Revise the spec, guides, design references, changelog, source skill and generated
  mirrors, and broad CLI journeys (`trading-2rc2`).
- [x] Verify frozen Python tests and lint; TypeScript lint, types, coverage, build, and
  package checks; every golden runtime and cross-implementation output comparison
  (`trading-jrva`, `trading-pkyo`, `trading-2rc2`).
- [ ] Integrate the exact commit into Metaproc and Trading consumer verification
  (`trading-y277`).
- [ ] Publish coordinated 0.9.0 releases and migrate released consumer dependency ranges
  (`trading-44ot`); this remains separate from source implementation completion.

Shared vectors own portable evidence cases; adapter tests own model identity, callback
exceptions, and engine-specific progress.
Extend the existing per-language model CLI journeys with a semantic rejection beside a
structural success. Regenerate whole result transcripts through the configured golden
runner, review the changes, and retain the existing golden fixture ownership rules.

## Verification Record

The final source passes 251 Python tests and the complete Python lint suite (Ruff,
BasedPyright, codespell, documentation footers, and retired-surface checks).
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
Exact committed-source pins and Trading consumer verification remain the responsibility
of `trading-y277`; publication remains `trading-44ot`.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
