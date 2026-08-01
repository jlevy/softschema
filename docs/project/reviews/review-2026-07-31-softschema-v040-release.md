---
title: softschema v0.4.0 Release Review
description: Senior engineering review and evidence record for the paired release
author: Codex, with maintainer direction from Joshua Levy
---
# Review: softschema v0.4.0 Release

**Date:** 2026-07-31 (last updated 2026-08-01)

**Author:** Codex, with maintainer direction from Joshua Levy

**Status:** Ready for the release PR; publication waits on required hosted CI.

**Tracking:** release epic `ss-fyvp`

## Decision

The merged timestamp design and final dependency graph are suitable for a minor release.
Its public contract is coherent, the migration is bounded, and the paired implementation
has direct unit, vector, golden, and cross-runtime coverage.
Local release approval is complete.
Publication remains conditioned on the release PR’s required CI and the immutable tag
and registry checks below.

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

The final TypeScript audit also found two high-severity host-confusion advisories in
Ajv’s locked `fast-uri` 3.1.2 dependency: GHSA-4c8g-83qw-93j6 (CVE-2026-13676) and
GHSA-v2hh-gcrm-f6hx (CVE-2026-16221). Version 3.1.4 is the first 3.x release that
contains both upstream fixes.
The exact tag and security patch, npm publisher and integrity, and advisory ranges were
reviewed. The maintainer explicitly approved a one-package release-age exception.
An exact root override now forces every Ajv edge in the checked-in Bun graph to 3.1.4;
users refresh their application lockfiles during the documented upgrade and verify the
same minimum. The reviewed v3.1.4 tag is commit `6aeece6`; its security change is commit
`2d50fba`. npm published it at `2026-07-19T07:42:54.497Z` with integrity
`sha512-8JnbkQ4juDyvYs4mgFGQqg4yCYtFDtUtmp2QIQq11ZZe5CFQ5wcqm1rqDgAh/QdMySuBnPzMUiJUNZG5N/AiQw==`.
The authoritative advisory records are
[GHSA-4c8g-83qw-93j6](https://github.com/advisories/GHSA-4c8g-83qw-93j6) and
[GHSA-v2hh-gcrm-f6hx](https://github.com/advisories/GHSA-v2hh-gcrm-f6hx).

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
| Vulnerable transitive TypeScript URI parser | Exact 3.1.4 override, source review, audit, clean-install tree check | Applications must refresh old lockfiles |
| Package versions diverge | Commit npm `0.4.0`; publish guard checks tag and artifacts | None after guard passes |
| Only one registry publishes | Rerun failed jobs using the retained candidate | Temporary registry skew |
| Registry index propagation lags | Query API/simple index and retry refreshed exact version | Short verification delay |

No risk requires a compatibility shim or another product mechanism.

## Validation Record

### Dependency Gate

| Check | Result |
| --- | --- |
| Upstream tag, release, PyPI version, and commit | Pass; tag and release target `78e0dd4`, and PyPI reports v0.4.0 |
| v0.3.0 to v0.4.0 source, release-note, and dependency review | Pass; tagged tree equals reviewed release-branch commit `f586298` |
| Date/timestamp contract consistency | Pass; generic YAML-native values and softschema portable strings are explicitly separated |
| `new_yaml` compatibility and upstream tests | Pass; 51 upstream tests plus exact v0.4.0 wheel and sdist validation and installation |
| Softschema minimum, cool-off exception, and lock update | Pass; minimum is v0.4.0, lock resolves v0.4.0, and all three CI syncs pass both exact exceptions |
| TypeScript URI dependency | Pass; reviewed `fast-uri` 3.1.4 override replaces vulnerable 3.1.2 and `bun audit` is clean |

The PyPI v0.4.0 artifacts have SHA-256 values
`71d6b416c6b05242d934b6228d2386311f2f9216d4d1d47549e6cadf7963fe76` for the wheel and
`dd7bc579b50e12a236c03427826a9af14fd2029e20dcae927e68f7440538e75a` for the source
distribution. They exactly match the candidates built from the reviewed branch before
release.
The unannotated tag points to merge commit `78e0dd4`, whose tree is identical to
`f586298`; the GitHub release targets that commit.
PyPI uploaded the final source distribution at `2026-08-01T01:26:20.316336Z`, the
timestamp used for the narrow first-party cool-off exception.
The existing `strif` CI exception now also uses its full RFC3339 timestamp, avoiding
timezone-dependent normalization of the previous date-only CLI value.

Isolated probes installed both registry artifacts.
The wheel probe verified that the generic reader constructs a Python `date` and the
generic writer quotes a date-looking string.
The earlier cross-package probe additionally verified that softschema retains the same
plain scalar as a string and that the new writer emits shared compiled-schema values
without anchors.

### Local Automated and Parity Checks

| Check | Result |
| --- | --- |
| Lint and type checks | Pass; codespell, Ruff, BasedPyright, Biome, and TypeScript clean |
| Python unit tests | Pass; 167 passed on Python 3.14.6 with `frontmatter-format` 0.4.0 installed |
| TypeScript unit tests and coverage | Pass; 171 passed; 96.06% functions and 96.35% lines |
| Python, Node, and Bun golden corpora | Pass; 38, 36, and 38 journeys |
| Direct cross-implementation comparison | Pass; all 20 command comparisons equal |
| Python and TypeScript builds plus `publint` | Pass; wheel, sdist, npm build, and `publint` succeeded |
| Dependency audits | Pass; hash-locked Python runtime, frozen Bun graph, and clean npm consumer report no known vulnerabilities |
| Markdown and generated-resource drift | Pass; formatter, generated section, and managed skill mirrors are idempotent |

These results are from the final dependency locks and release tree.

### Clean Product Smokes

| Check | Result |
| --- | --- |
| Built wheel and sdist | Pass; exact v0.4.0 candidates install separately, report both softschema and `frontmatter-format` 0.4.0, and load bundled docs |
| Built npm tarball under plain Node | Pass; exact v0.4.0 candidate installs, reports 0.4.0, exposes the ESM library and CLI, resolves `fast-uri` 3.1.4, and audits clean |
| README quickstart under both implementations | Pass; exact installed candidates validate with zero flags and emit byte-identical artifacts and schemas |
| Project skill installation | Pass; exact wheel creates byte-identical portable and Claude mirrors reporting version 0.4.0 |

The exact simulated v0.4.0 candidates have SHA-256 values
`97a039d94328835284de990b13e56ed858b44bcebfe908b7a7cf106618cb63c7` for the wheel,
`338fa9869ec23dff8928c7aac045132321bbaf52de234f0f470a65e581429078` for the source
distribution, and `740992b3d09d0d1601d596952a223ba1c46d886169d1142e8e250bcb25f7df97` for
the npm tarball. Hosted release candidates are rebuilt from the green commit and carry
their own transferred checksum record; these local hashes prove the candidate shape
rather than predict cross-run archive bytes.

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
