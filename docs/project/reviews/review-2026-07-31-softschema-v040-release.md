---
title: softschema v0.4.0 Release Review
description: Senior engineering review and evidence record for the paired release
author: Codex, with maintainer direction from Joshua Levy
---
# Review: softschema v0.4.0 Release

**Date:** 2026-07-31 (last updated 2026-07-31)

**Author:** Codex, with maintainer direction from Joshua Levy

**Status:** In progress; release approval waits on the final dependency and validation
evidence below.

**Tracking:** release epic `ss-fyvp`

## Decision

The merged timestamp design is suitable for a minor release.
Its public contract is coherent, the migration is bounded, and the paired implementation
has direct unit, vector, golden, and cross-runtime coverage.
Publication is approved only after the `frontmatter-format` v0.4.0 gate and the final
validation record are complete.

No design decision remains open.
The outstanding entries are execution evidence, not deferred product questions.

## Scope Reviewed

The aggregate release delta begins at tag `v0.3.0` and includes:

- PR #23: portable timestamp string decoding, canonical temporal-schema parity, tests,
  examples, agent guidance, and public documentation;
- the shared package version bump and v0.4.0 release notes;
- adoption of first-party `frontmatter-format` v0.4.0 after source review;
- project-spec archival, release-runbook corrections, and formatter isolation from
  ambient uv configuration.

The review covers the artifact contract, both library and CLI surfaces, generated
schemas, migration guidance, documentation ownership, dependency policy, package
contents, CI and OIDC publication, failure recovery, and registry verification.

## Engineering Assessment

### Artifact and API Contract

The design chooses the smallest portable contract: YAML date-shaped values are strings.
It avoids a second artifact version, runtime-specific temporal objects, coercion, and a
compatibility mode. Existing values do not need rewriting.
The only acceptance change is deliberate: previously rejected bare date and timestamp
scalars now parse.

The structural and semantic layers stay correctly separated.
Canonical schemas retain `format` annotations while softschema does not enable the
optional Format-Assertion vocabulary.
Explicit portable keywords remain structural; Pydantic and Zod remain the semantic
authority for their respective hosts.

### Cross-Runtime Parity

The relevant parity promise is structural meaning, string values, stable errors, and
canonical schema identity.
It is not identical Pydantic and Zod semantic behavior.
Tests cover quoted and unquoted temporal strings, valid and invalid spellings, explicit
tags, canonical Pydantic/Zod output, retained authored patterns, compiler immutability,
and host-model semantic validation.

### Upgrade Path

The changelog gives a complete sequence for low-context users: upgrade every softschema
implementation in use, keep paired consumers at one version, refresh lockfiles, validate
all artifacts, regenerate affected Zod schemas, restore any intended structural pattern
explicitly, test semantic models, retain string-valued results, and refresh managed
skill mirrors. This is sufficient for agents to migrate existing repositories without a
runtime migration command.

### Documentation Architecture

Exact format rules remain in the spec.
The guide owns rationale and migration examples; the language design docs own
runtime-specific mechanics; the skill carries concise agent rules; the changelog owns
the versioned upgrade path.
The README remains concise.
All edited repository docs use present-state language, low-context framing, descriptive
links, and the standard common-doc footer.

### Release and Supply Chain

The release flow builds wheel, sdist, and npm tarball candidates once, records and
verifies checksums, installs the transferred candidates on supported systems, and gives
OIDC publication authority only to release jobs.
The Python version derives from the tag; CI checks it against the committed npm version.
Prior v0.3.0 publication proves both trusted-publisher relationships.

The standard cool-off remains in place.
The new `frontmatter-format` version receives a narrow, timestamped exception because it
is first-party and explicitly approved.
CI must repeat the exception anywhere `UV_EXCLUDE_NEWER` replaces the project map.

### Related-Format and Timestamp Consistency

The two v0.4 releases have compatible but deliberately different value contracts.
`frontmatter-format` defines general frontmatter fences and YAML handling: its readers
accept aliases and YAML timestamps, Python `date` and `datetime` inputs serialize as
timestamps, and ISO date-looking strings remain quoted strings.
Its v0.4 release changes automatic alias output and adds raw in-memory splitting; it
does not change timestamp semantics or define a JSON-compatible value subset.

softschema defines a stricter artifact profile.
It owns frontmatter extraction and portable YAML parsing, retains implicit date- and
timestamp-shaped scalars as strings, and uses `frontmatter-format` only to write
compiled-schema YAML. Consequently the softschema timestamp change does not depend on or
contradict the dependency’s generic reader behavior.
The spec, guide, Python design, and release notes now state this boundary explicitly.

### Failure Recovery

Before tagging, failures return to the release branch.
After tagging, tags and published versions are immutable: a failed registry job is rerun
against the same checksummed candidate, while a defective published artifact is
corrected in v0.4.1. The process does not move tags, overwrite versions, or rebuild
release bytes locally.

## Risk Review

| Risk | Control | Residual risk |
| --- | --- | --- |
| Consumer expected v0.3 timestamp rejection | Minor-version notes and full-corpus validation | Intentional accepted-input expansion |
| Zod schema digest changes | Explicit regeneration and diff review | One-time generated-file churn |
| Pydantic and Zod semantics differ | Require application-level semantic tests | Model libraries remain independently configurable |
| New first-party dependency regression | Tagged-source review, focused tests, lock review, full package smokes | Ordinary upstream maintenance risk |
| Package versions diverge | Commit npm `0.4.0`; publish guard checks tag and artifacts | None after guard passes |
| Only one registry publishes | Rerun failed jobs using the retained candidate | Temporary registry skew |
| Registry index propagation lags | Query API/simple index and retry refreshed exact version | Short verification delay |

No risk requires a compatibility shim or another product mechanism.

## Validation Record

### Dependency Gate

| Check | Result |
| --- | --- |
| Upstream tag, release, PyPI version, and commit | Pending release |
| v0.3.0 to v0.4.0 source, release-note, and dependency review | Pass at release-branch commit `f586298`; final tag comparison pending |
| Date/timestamp contract consistency | Pass; generic YAML-native values and softschema portable strings are explicitly separated |
| `new_yaml` compatibility and upstream tests | Pass; 51 upstream tests plus exact v0.4.0 wheel and sdist validation and installation |
| Softschema minimum, cool-off exception, and lock update | Pending release |

The simulated v0.4.0 artifacts from the reviewed release branch had SHA-256 values
`71d6b416c6b05242d934b6228d2386311f2f9216d4d1d47549e6cadf7963fe76` for the wheel and
`dd7bc579b50e12a236c03427826a9af14fd2029e20dcae927e68f7440538e75a` for the source
distribution. An isolated integration probe installed that wheel with the softschema
wheel and verified all four boundary properties: the generic reader constructs a Python
`date`, the generic writer quotes a date-looking string, softschema retains the same
plain scalar as a string, and the new writer emits shared compiled-schema values without
anchors. The final tagged artifacts are rebuilt and rechecked; these branch-candidate
hashes are evidence, not expected registry hashes.

### Local Automated and Parity Checks

| Check | Result |
| --- | --- |
| Lint and type checks | Preliminary pass; lint, Ruff, BasedPyright, Biome, and TypeScript clean |
| Python unit tests | Preliminary pass; 167 passed on Python 3.14.6 |
| TypeScript unit tests and coverage | Preliminary pass; 171 passed; 96.06% functions and 96.35% lines |
| Python, Node, and Bun golden corpora | Preliminary pass; 38, 36, and 38 journeys |
| Direct cross-implementation comparison | Preliminary pass; all 20 command comparisons equal |
| Python and TypeScript builds plus `publint` | Preliminary pass; wheel, sdist, npm build, and `publint` succeeded |
| Markdown and generated-resource drift | Preliminary formatter pass complete; final idempotence check pending dependency |

These are dependency-independent baseline results from the release branch.
The complete table is rerun and replaced with final evidence after `frontmatter-format`
v0.4.0 is locked.

### Clean Product Smokes

| Check | Result |
| --- | --- |
| Built wheel and sdist | Preliminary pass; clean wheel install reported the expected pre-tag development version |
| Built npm tarball under plain Node | Preliminary pass; clean tarball install reported `softschema 0.4.0` |
| README quickstart under both implementations | Preliminary pass from clean temporary directories |
| Project skill installation | Preliminary pass; portable and Claude mirrors created in a scratch Git repository |

The clean product smokes are repeated against the final dependency and release
candidates before publication.

### Hosted Release Evidence

| Check | Result |
| --- | --- |
| Release PR and required CI | Pending |
| `v0.4.0` tag and GitHub release | Pending |
| Publish workflow and candidate checksums | Pending |
| PyPI exact-version install | Pending |
| npm exact-version install | Pending |
| Published quickstart | Pending |

## Release Approval Gate

Approve publication only when every table row is complete, the final aggregate diff has
no unexplained file, the worktree is clean, the tag target is the green release PR merge
commit, and the public release notes match the changelog’s behavior and migration steps.

## References

- [v0.4.0 Release Plan](../specs/active/plan-2026-07-31-softschema-v040-release.md)
- [Portable YAML Timestamp Strings](../specs/done/plan-2026-07-31-portable-yaml-timestamps.md)
- [End-to-End Testing Runbook](../../e2e-testing.runbook.md)
- [Publishing](../../publishing.md)
- [Changelog](../../../CHANGELOG.md)
- [Merged implementation PR #23](https://github.com/jlevy/softschema/pull/23)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
